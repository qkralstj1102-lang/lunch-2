import re
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st
import plotly.express as px


# =========================
# 기본 설정
# =========================

st.set_page_config(
    page_title="학교 급식 데이터",
    page_icon="🍚",
    layout="wide"
)

SCHOOL_API = "https://open.neis.go.kr/hub/schoolInfo"
MEAL_API = "https://open.neis.go.kr/hub/mealServiceDietInfo"

API_KEY = st.secrets["NEIS_API_KEY"]


# =========================
# 학교 검색
# =========================

@st.cache_data
def search_school(school_name):
    params = {
        "KEY": API_KEY,
        "Type": "json",
        "SCHUL_NM": school_name
    }

    response = requests.get(SCHOOL_API, params=params, timeout=10)
    data = response.json()

    try:
        rows = data["schoolInfo"][1]["row"]
    except (KeyError, IndexError):
        return []

    result = []

    for row in rows:
        result.append({
            "학교명": row.get("SCHUL_NM", ""),
            "교육청코드": row.get("ATPT_OFCDC_SC_CODE", ""),
            "학교코드": row.get("SD_SCHUL_CODE", ""),
            "지역": row.get("LCTN_SC_NM", "")
        })

    return result


# =========================
# 급식 데이터 가져오기
# =========================

@st.cache_data
def get_meal_data(
    office_code,
    school_code,
    start_date,
    end_date
):
    params = {
        "KEY": API_KEY,
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
        "MMEAL_SC_CODE": "2",
        "MLSV_FROM_YMD": start_date,
        "MLSV_TO_YMD": end_date,
        "pSize": 1000,
        "pIndex": 1
    }

    response = requests.get(MEAL_API, params=params, timeout=10)
    data = response.json()

    try:
        rows = data["mealServiceDietInfo"][1]["row"]
    except (KeyError, IndexError):
        return pd.DataFrame()

    result = []

    for row in rows:
        cal_info = row.get("CAL_INFO", "")
        ntr_info = row.get("NTR_INFO", "")
        menu = row.get("DDISH_NM", "")

        # 칼로리 숫자 추출
        calorie_match = re.search(
            r"[\d,]+(?:\.\d+)?",
            cal_info
        )

        if calorie_match:
            calorie = float(
                calorie_match.group().replace(",", "")
            )
        else:
            calorie = None

        result.append({
            "날짜": pd.to_datetime(
                row.get("MLSV_YMD"),
                format="%Y%m%d",
                errors="coerce"
            ),
            "칼로리": calorie,
            "메뉴": menu,
            "영양정보": ntr_info
        })

    return pd.DataFrame(result)


# =========================
# 오늘 급식 가져오기
# =========================

@st.cache_data
def get_today_meal(
    office_code,
    school_code
):
    today = date.today().strftime("%Y%m%d")

    params = {
        "KEY": API_KEY,
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
        "MMEAL_SC_CODE": "2",
        "MLSV_FROM_YMD": today,
        "MLSV_TO_YMD": today,
        "pSize": 100,
        "pIndex": 1
    }

    response = requests.get(
        MEAL_API,
        params=params,
        timeout=10
    )

    data = response.json()

    try:
        rows = data["mealServiceDietInfo"][1]["row"]
    except (KeyError, IndexError):
        return None

    if not rows:
        return None

    return rows[0]


# =========================
# 사이드바
# =========================

st.sidebar.title("🍚 학교 급식 데이터")

page = st.sidebar.radio(
    "페이지 선택",
    [
        "🏠 메인페이지",
        "📊 급식 데이터 분석"
    ]
)


# ==========================================================
# 1. 메인페이지
# ==========================================================

if page == "🏠 메인페이지":

    st.title("🍚 오늘의 학교 급식")
    st.write("학교를 선택하면 오늘의 급식과 칼로리, 영양정보를 확인할 수 있습니다.")

    st.divider()

    # 학교 검색
    st.subheader("🏫 학교 선택")

    school_name = st.text_input(
        "학교 이름을 입력하세요",
        value="송탄고등학교"
    )

    if school_name:

        schools = search_school(school_name)

        if len(schools) == 0:
            st.warning("검색된 학교가 없습니다.")

        else:

            school_options = [
                f"{school['학교명']} ({school['지역']})"
                for school in schools
            ]

            selected_index = st.selectbox(
                "학교를 선택하세요",
                range(len(school_options)),
                format_func=lambda x: school_options[x]
            )

            selected_school = schools[selected_index]

            st.success(
                f"선택한 학교: {selected_school['학교명']}"
            )

            # 오늘 급식 가져오기
            today_meal = get_today_meal(
                selected_school["교육청코드"],
                selected_school["학교코드"]
            )

            st.divider()

            if today_meal is None:

                st.info(
                    "오늘은 등록된 급식 데이터가 없습니다."
                )

            else:

                st.subheader("🍱 오늘의 점심")

                # 메뉴
                menu = today_meal.get("DDISH_NM", "")

                # <br/> 제거
                menu_list = re.split(
                    r"<br\s*/?>",
                    menu
                )

                menu_list = [
                    re.sub(
                        r"\([0-9.,]+\)",
                        "",
                        item
                    ).strip()
                    for item in menu_list
                    if item.strip()
                ]

                # 메뉴 표시
                for item in menu_list:
                    st.write(f"• {item}")

                st.divider()

                # 칼로리
                cal_info = today_meal.get(
                    "CAL_INFO",
                    ""
                )

                calorie_match = re.search(
                    r"[\d,]+(?:\.\d+)?",
                    cal_info
                )

                if calorie_match:
                    calorie = float(
                        calorie_match.group().replace(",", "")
                    )

                    st.metric(
                        "🔥 오늘의 급식 칼로리",
                        f"{calorie:,.0f} kcal"
                    )
                else:
                    st.info(
                        "오늘의 칼로리 정보가 없습니다."
                    )

                st.divider()

                # 영양정보
                st.subheader("🥗 영양정보")

                ntr_info = today_meal.get(
                    "NTR_INFO",
                    ""
                )

                if ntr_info:

                    nutrition_list = re.split(
                        r"<br\s*/?>",
                        ntr_info
                    )

                    for item in nutrition_list:
                        item = item.strip()

                        if item:
                            st.write(f"• {item}")

                else:
                    st.info(
                        "오늘의 영양정보가 없습니다."
                    )


# ==========================================================
# 2. 급식 데이터 분석
# ==========================================================

elif page == "📊 급식 데이터 분석":

    st.title("📊 학교 급식 데이터 분석")

    st.write(
        "여러 학교의 급식 칼로리를 비교하고 "
        "날짜와 요일에 따른 차이를 분석합니다."
    )

    st.divider()

    # -------------------------
    # 날짜 설정
    # -------------------------

    st.sidebar.subheader("📅 분석 기간")

    default_end = date.today()
    default_start = default_end - timedelta(days=30)

    date_range = st.sidebar.date_input(
        "기간 선택",
        value=(default_start, default_end)
    )

    if len(date_range) != 2:
        st.warning("시작 날짜와 끝 날짜를 모두 선택해주세요.")
        st.stop()

    start_date, end_date = date_range

    # -------------------------
    # 학교 검색
    # -------------------------

    st.sidebar.subheader("🏫 학교 추가")

    search_name = st.sidebar.text_input(
        "학교 이름 검색",
        value=""
    )

    if search_name:

        search_results = search_school(search_name)

        if search_results:

            school_names = [
                f"{x['학교명']} ({x['지역']})"
                for x in search_results
            ]

            selected_search = st.sidebar.selectbox(
                "검색 결과",
                range(len(search_results)),
                format_func=lambda x: school_names[x]
            )

            selected = search_results[selected_search]

            if st.sidebar.button("➕ 비교 학교에 추가"):

                if "schools" not in st.session_state:
                    st.session_state.schools = []

                if selected not in st.session_state.schools:
                    st.session_state.schools.append(selected)

                    st.sidebar.success(
                        f"{selected['학교명']} 추가됨"
                    )

        else:
            st.sidebar.warning(
                "검색된 학교가 없습니다."
            )

    # -------------------------
    # 송탄고등학교 기본 추가
    # -------------------------

    if "schools" not in st.session_state:

        st.session_state.schools = []

        songtan = search_school("송탄고등학교")

        for school in songtan:

            if school["학교명"] == "송탄고등학교":
                st.session_state.schools.append(school)
                break

    # -------------------------
    # 학교 선택
    # -------------------------

    # 학교 정보가 올바른 형태인지 확인
valid_schools = []

for school in st.session_state.schools:
    if isinstance(school, dict) and "학교명" in school:
        valid_schools.append(school)

st.session_state.schools = valid_schools

school_names = [
    school["학교명"]
    for school in st.session_state.schools
]

    if len(school_names) == 0:

        st.info(
            "왼쪽에서 비교할 학교를 추가해주세요."
        )
        st.stop()

    selected_names = st.sidebar.multiselect(
        "비교할 학교 선택",
        school_names,
        default=school_names
    )

    if len(selected_names) < 3:

        st.warning(
            "비교하려면 최소 3개의 학교를 선택해주세요."
        )
        st.stop()

    selected_schools = [
        school
        for school in st.session_state.schools
        if school["학교명"] in selected_names
    ]

    # -------------------------
    # 데이터 수집
    # -------------------------

    all_data = []

    for school in selected_schools:

        df = get_meal_data(
            school["교육청코드"],
            school["학교코드"],
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d")
        )

        if not df.empty:

            df["학교명"] = school["학교명"]

            all_data.append(df)

    if not all_data:

        st.error(
            "선택한 기간에 급식 데이터가 없습니다."
        )
        st.stop()

    df_all = pd.concat(
        all_data,
        ignore_index=True
    )

    # -------------------------
    # 기본 통계
    # -------------------------

    st.subheader("📌 기본 통계")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "분석 학교 수",
        f"{len(selected_schools)}개"
    )

    col2.metric(
        "급식 데이터 수",
        f"{len(df_all)}개"
    )

    col3.metric(
        "전체 평균 칼로리",
        f"{df_all['칼로리'].mean():,.0f} kcal"
    )

    # -------------------------
    # 그래프 1
    # -------------------------

    st.subheader("1️⃣ 학교별 평균 급식 칼로리")

    school_avg = (
        df_all
        .groupby("학교명")["칼로리"]
        .mean()
        .reset_index()
    )

    fig1 = px.bar(
        school_avg,
        x="학교명",
        y="칼로리",
        text_auto=".0f",
        title="학교별 평균 급식 칼로리"
    )

    fig1.update_layout(
        xaxis_title="학교",
        yaxis_title="평균 칼로리(kcal)"
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

    # -------------------------
    # 그래프 2
    # -------------------------

    st.subheader("2️⃣ 날짜별 급식 칼로리")

    fig2 = px.line(
        df_all.sort_values("날짜"),
        x="날짜",
        y="칼로리",
        color="학교명",
        markers=True,
        title="학교별 날짜에 따른 급식 칼로리 변화"
    )

    fig2.update_layout(
        xaxis_title="날짜",
        yaxis_title="칼로리(kcal)"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # -------------------------
    # 통계표
    # -------------------------

    st.subheader("📋 학교별 통계")

    stats = (
        df_all
        .groupby("학교명")["칼로리"]
        .agg(
            평균="mean",
            최댓값="max",
            최솟값="min",
            데이터수="count"
        )
        .reset_index()
    )

    stats["평균"] = stats["평균"].round(1)

    st.dataframe(
        stats,
        use_container_width=True,
        hide_index=True
    )

    # ======================================================
    # 추가 질문
    # ======================================================

    st.divider()

    st.subheader(
        "🔎 추가 질문"
    )

    st.markdown(
        "### 송탄고등학교와 주변 학교의 급식 칼로리는 "
        "요일에 따라 어떤 차이를 보일까?"
    )

    weekday_order = [
        "월요일",
        "화요일",
        "수요일",
        "목요일",
        "금요일"
    ]

    df_weekday = df_all.copy()

    df_weekday["요일"] = (
        df_weekday["날짜"]
        .dt.dayofweek
        .map({
            0: "월요일",
            1: "화요일",
            2: "수요일",
            3: "목요일",
            4: "금요일"
        })
    )

    df_weekday = df_weekday[
        df_weekday["요일"].isin(weekday_order)
    ]

    weekday_avg = (
        df_weekday
        .groupby(["학교명", "요일"])["칼로리"]
        .mean()
        .reset_index()
    )

    weekday_avg["요일"] = pd.Categorical(
        weekday_avg["요일"],
        categories=weekday_order,
        ordered=True
    )

    weekday_avg = weekday_avg.sort_values("요일")

    # -------------------------
    # 요일별 학교 비교 그래프
    # -------------------------

    st.write("### 3️⃣ 요일별 평균 급식 칼로리")

    fig3 = px.line(
        weekday_avg,
        x="요일",
        y="칼로리",
        color="학교명",
        markers=True,
        title="학교별 요일에 따른 평균 급식 칼로리"
    )

    fig3.update_layout(
        xaxis_title="요일",
        yaxis_title="평균 칼로리(kcal)"
    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )

    # -------------------------
    # 요일별 전체 평균
    # -------------------------

    overall_weekday = (
        df_weekday
        .groupby("요일")["칼로리"]
        .mean()
        .reset_index()
    )

    overall_weekday["요일"] = pd.Categorical(
        overall_weekday["요일"],
        categories=weekday_order,
        ordered=True
    )

    overall_weekday = overall_weekday.sort_values("요일")

    st.write("### 4️⃣ 요일별 전체 평균")

    fig4 = px.bar(
        overall_weekday,
        x="요일",
        y="칼로리",
        text_auto=".0f",
        title="요일별 전체 평균 급식 칼로리"
    )

    fig4.update_layout(
        xaxis_title="요일",
        yaxis_title="평균 칼로리(kcal)"
    )

    st.plotly_chart(
        fig4,
        use_container_width=True
    )

    # -------------------------
    # 요일별 학교 비교표
    # -------------------------

    st.write("### 📋 학교별 요일 평균")

    weekday_table = weekday_avg.pivot(
        index="학교명",
        columns="요일",
        values="칼로리"
    )

    weekday_table = weekday_table.round(1)

    st.dataframe(
        weekday_table,
        use_container_width=True
    )
    
