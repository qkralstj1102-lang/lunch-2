import re
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st
import plotly.express as px


# =========================================================
# 기본 설정
# =========================================================

st.set_page_config(
    page_title="학교 급식 데이터",
    page_icon="🍚",
    layout="wide"
)

SCHOOL_API = "https://open.neis.go.kr/hub/schoolInfo"
MEAL_API = "https://open.neis.go.kr/hub/mealServiceDietInfo"

API_KEY = st.secrets["NEIS_API_KEY"]


# =========================================================
# 학교 검색 함수
# =========================================================

@st.cache_data
def search_school(school_name):

    params = {
        "KEY": API_KEY,
        "Type": "json",
        "SCHUL_NM": school_name
    }

    try:
        response = requests.get(
            SCHOOL_API,
            params=params,
            timeout=10
        )

        data = response.json()

        rows = data["schoolInfo"][1]["row"]

    except Exception:
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


# =========================================================
# 급식 데이터 함수
# =========================================================

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

    try:
        response = requests.get(
            MEAL_API,
            params=params,
            timeout=10
        )

        data = response.json()

        rows = data["mealServiceDietInfo"][1]["row"]

    except Exception:
        return pd.DataFrame()

    result = []

    for row in rows:

        cal_info = row.get("CAL_INFO", "")
        menu = row.get("DDISH_NM", "")
        ntr_info = row.get("NTR_INFO", "")

        # 칼로리 추출
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


# =========================================================
# 오늘 급식 함수
# =========================================================

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

    try:
        response = requests.get(
            MEAL_API,
            params=params,
            timeout=10
        )

        data = response.json()

        rows = data["mealServiceDietInfo"][1]["row"]

    except Exception:
        return None

    if not rows:
        return None

    return rows[0]


# =========================================================
# 세션 초기화
# =========================================================

if "schools" not in st.session_state:
    st.session_state.schools = []

# 혹시 이전 실행에서 잘못된 데이터가 남아 있으면 제거
st.session_state.schools = [
    school
    for school in st.session_state.schools
    if isinstance(school, dict)
    and "학교명" in school
    and "교육청코드" in school
    and "학교코드" in school
]


# =========================================================
# 송탄고등학교 기본 등록
# =========================================================

if len(st.session_state.schools) == 0:

    songtan_results = search_school("송탄고등학교")

    for school in songtan_results:

        if school["학교명"] == "송탄고등학교":

            st.session_state.schools.append(school)
            break


# =========================================================
# 사이드바
# =========================================================

st.sidebar.title("🍚 학교 급식 데이터")

page = st.sidebar.radio(
    "페이지 선택",
    [
        "🏠 메인페이지",
        "📊 급식 데이터 분석"
    ]
)


# =========================================================
# PAGE 1 : 메인페이지
# =========================================================

if page == "🏠 메인페이지":

    st.title("🍚 오늘의 학교 급식")

    st.write(
        "학교를 선택하면 오늘의 급식 메뉴와 "
        "칼로리, 영양정보를 확인할 수 있습니다."
    )

    st.divider()

    st.subheader("🏫 학교 선택")

    school_search = st.text_input(
        "학교 이름을 검색하세요",
        value="송탄고등학교"
    )

    if school_search:

        results = search_school(school_search)

        if not results:

            st.warning(
                "검색된 학교가 없습니다. 학교 이름을 다시 확인해주세요."
            )

        else:

            # 검색 결과를 문자열로 표시
            options = []

            for school in results:

                options.append(
                    f"{school['학교명']} ({school['지역']})"
                )

            selected_option = st.selectbox(
                "검색 결과에서 학교를 선택하세요",
                options
            )

            selected_index = options.index(
                selected_option
            )

            selected_school = results[selected_index]

            st.success(
                f"선택한 학교: {selected_school['학교명']}"
            )

            # 오늘 급식
            today_meal = get_today_meal(
                selected_school["교육청코드"],
                selected_school["학교코드"]
            )

            st.divider()

            if today_meal is None:

                st.info(
                    "오늘 등록된 급식 정보가 없습니다."
                )

            else:

                # =================================================
                # 오늘의 급식 메뉴
                # =================================================

                st.subheader("🍱 오늘의 점심")

                menu = today_meal.get(
                    "DDISH_NM",
                    ""
                )

                menu_list = re.split(
                    r"<br\s*/?>",
                    menu
                )

                for item in menu_list:

                    item = item.strip()

                    if item:

                        # 알레르기 번호 제거
                        item = re.sub(
                            r"\([0-9.,]+\)",
                            "",
                            item
                        )

                        st.write(
                            f"• {item.strip()}"
                        )

                st.divider()

                # =================================================
                # 칼로리
                # =================================================

                st.subheader("🔥 오늘의 칼로리")

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
                        "급식 칼로리",
                        f"{calorie:,.0f} kcal"
                    )

                else:

                    st.info(
                        "칼로리 정보가 없습니다."
                    )

                st.divider()

                # =================================================
                # 영양정보
                # =================================================

                st.subheader("🥗 오늘의 영양정보")

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

                            st.write(
                                f"• {item}"
                            )

                else:

                    st.info(
                        "영양정보가 없습니다."
                    )


# =========================================================
# PAGE 2 : 급식 데이터 분석
# =========================================================

elif page == "📊 급식 데이터 분석":

    st.title("📊 학교 급식 데이터 분석")

    st.write(
        "여러 학교의 급식 칼로리를 비교하고 "
        "날짜와 요일에 따른 차이를 분석합니다."
    )

    st.divider()

    # =====================================================
    # 분석 기간
    # =====================================================

    st.sidebar.subheader("📅 분석 기간")

    today = date.today()

    default_start = today - timedelta(days=30)

    date_range = st.sidebar.date_input(
        "분석할 기간",
        value=(default_start, today)
    )

    if len(date_range) != 2:

        st.warning(
            "시작 날짜와 종료 날짜를 모두 선택해주세요."
        )

        st.stop()

    start_date = date_range[0]
    end_date = date_range[1]

    # =====================================================
    # 학교 검색
    # =====================================================

    st.sidebar.subheader("🏫 비교 학교 추가")

    search_name = st.sidebar.text_input(
        "학교 이름 검색",
        key="analysis_school_search"
    )

    if search_name:

        search_results = search_school(
            search_name
        )

        if not search_results:

            st.sidebar.warning(
                "검색된 학교가 없습니다."
            )

        else:

            result_names = []

            for school in search_results:

                result_names.append(
                    f"{school['학교명']} ({school['지역']})"
                )

            selected_result = st.sidebar.selectbox(
                "검색 결과",
                result_names,
                key="analysis_school_result"
            )

            selected_index = result_names.index(
                selected_result
            )

            selected_school = search_results[
                selected_index
            ]

            if st.sidebar.button(
                "➕ 비교 학교에 추가"
            ):

                already_exists = False

                for school in st.session_state.schools:

                    if (
                        school["학교명"]
                        == selected_school["학교명"]
                        and
                        school["학교코드"]
                        == selected_school["학교코드"]
                    ):
                        already_exists = True
                        break

                if already_exists:

                    st.sidebar.info(
                        "이미 추가된 학교입니다."
                    )

                else:

                    st.session_state.schools.append(
                        selected_school
                    )

                    st.sidebar.success(
                        f"{selected_school['학교명']} 추가 완료!"
                    )

                    st.rerun()

    # =====================================================
    # 현재 등록된 학교
    # =====================================================

    school_names = [
        school["학교명"]
        for school in st.session_state.schools
    ]

    if not school_names:

        st.info(
            "왼쪽에서 비교할 학교를 추가해주세요."
        )

        st.stop()

    # =====================================================
    # 분석할 학교 선택
    # =====================================================

    selected_names = st.sidebar.multiselect(
        "분석할 학교 선택",
        school_names,
        default=school_names
    )

    if len(selected_names) < 3:

        st.warning(
            "학교 비교를 위해 최소 3개의 학교를 선택해주세요."
        )

        st.stop()

    selected_schools = []

    for school in st.session_state.schools:

        if school["학교명"] in selected_names:

            selected_schools.append(
                school
            )

    # =====================================================
    # 데이터 가져오기
    # =====================================================

    all_data = []

    progress = st.progress(0)

    total = len(selected_schools)

    for i, school in enumerate(
        selected_schools
    ):

        df = get_meal_data(
            school["교육청코드"],
            school["학교코드"],
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d")
        )

        if not df.empty:

            df["학교명"] = school["학교명"]

            all_data.append(df)

        progress.progress(
            (i + 1) / total
        )

    progress.empty()

    if not all_data:

        st.error(
            "선택한 기간에 급식 데이터가 없습니다."
        )

        st.stop()

    df_all = pd.concat(
        all_data,
        ignore_index=True
    )

    # 칼로리 없는 데이터 제거
    df_all = df_all.dropna(
        subset=["칼로리"]
    )

    # =====================================================
    # 기본 정보
    # =====================================================

    st.subheader("📌 분석 정보")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "분석 학교",
        f"{len(selected_schools)}개"
    )

    col2.metric(
        "급식 데이터",
        f"{len(df_all)}개"
    )

    col3.metric(
        "전체 평균",
        f"{df_all['칼로리'].mean():,.0f} kcal"
    )

    # =====================================================
    # 그래프 1
    # =====================================================

    st.subheader(
        "1️⃣ 학교별 평균 급식 칼로리"
    )

    school_avg = (
        df_all
        .groupby("학교명")["칼로리"]
        .mean()
        .reset_index()
    )

    school_avg["칼로리"] = school_avg[
        "칼로리"
    ].round(1)

    fig1 = px.bar(
        school_avg,
        x="학교명",
        y="칼로리",
        text_auto=".0f",
        title="학교별 평균 급식 칼로리"
    )

    fig1.update_layout(
        xaxis_title="학교",
        yaxis_title="평균 칼로리 (kcal)"
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

    # =====================================================
    # 그래프 2
    # =====================================================

    st.subheader(
        "2️⃣ 날짜별 급식 칼로리"
    )

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
        yaxis_title="칼로리 (kcal)"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # =====================================================
    # 통계표
    # =====================================================

    st.subheader(
        "📋 학교별 칼로리 통계"
    )

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

    # =====================================================
    # 추가 질문
    # =====================================================

    st.divider()

    st.subheader(
        "🔎 추가 질문"
    )

    st.markdown(
        "### 송탄고등학교와 주변 학교의 급식 칼로리는 "
        "요일에 따라 어떤 차이를 보일까?"
    )

    # =====================================================
    # 요일 데이터 만들기
    # =====================================================

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

    # 주말 제거
    df_weekday = df_weekday[
        df_weekday["요일"].isin(
            weekday_order
        )
    ]

    # =====================================================
    # 그래프 3 : 요일별 학교 평균
    # =====================================================

    st.subheader(
        "3️⃣ 요일별 평균 급식 칼로리"
    )

    weekday_avg = (
        df_weekday
        .groupby(
            ["학교명", "요일"]
        )["칼로리"]
        .mean()
        .reset_index()
    )

    weekday_avg["요일"] = pd.Categorical(
        weekday_avg["요일"],
        categories=weekday_order,
        ordered=True
    )

    weekday_avg = weekday_avg.sort_values(
        "요일"
    )

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
        yaxis_title="평균 칼로리 (kcal)"
    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )

    # =====================================================
    # 그래프 4 : 전체 요일 평균
    # =====================================================

    st.subheader(
        "4️⃣ 요일별 전체 평균 급식 칼로리"
    )

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

    overall_weekday = overall_weekday.sort_values(
        "요일"
    )

    fig4 = px.bar(
        overall_weekday,
        x="요일",
        y="칼로리",
        text_auto=".0f",
        title="요일별 전체 평균 급식 칼로리"
    )

    fig4.update_layout(
        xaxis_title="요일",
        yaxis_title="평균 칼로리 (kcal)"
    )

    st.plotly_chart(
        fig4,
        use_container_width=True
    )

    # =====================================================
    # 요일별 표
    # =====================================================

    st.subheader(
        "📋 학교별 요일 평균"
    )

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

    # =====================================================
    # 분석 결과 간단 표시
    # =====================================================

    if not overall_weekday.empty:

        highest_day = overall_weekday.loc[
            overall_weekday["칼로리"].idxmax()
        ]

        lowest_day = overall_weekday.loc[
            overall_weekday["칼로리"].idxmin()
        ]

        st.divider()

        st.subheader(
            "💡 요일별 분석 결과"
        )

        col1, col2 = st.columns(2)

        col1.metric(
            "평균 칼로리가 가장 높은 요일",
            highest_day["요일"],
            f"{highest_day['칼로리']:.0f} kcal"
        )

        col2.metric(
            "평균 칼로리가 가장 낮은 요일",
            lowest_day["요일"],
            f"{lowest_day['칼로리']:.0f} kcal"
        )
