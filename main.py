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
    page_title="학교 급식 칼로리 비교",
    page_icon="🍱",
    layout="wide"
)

st.title("🍱 학교 급식 칼로리 비교")
st.caption("송탄고등학교와 주변 학교의 급식 평균 칼로리를 비교해 봅니다.")

SCHOOL_API = "https://open.neis.go.kr/hub/schoolInfo"
MEAL_API = "https://open.neis.go.kr/hub/mealServiceDietInfo"


# =========================
# API 키
# =========================

try:
    API_KEY = st.secrets["NEIS_API_KEY"]
except Exception:
    st.error("NEIS API 키가 설정되지 않았습니다.")
    st.info(
        "Streamlit Cloud → Manage app → Settings → Secrets에서 "
        'NEIS_API_KEY = "발급받은 API 키" 형식으로 입력하세요.'
    )
    st.stop()


# =========================
# 학교 검색
# =========================

@st.cache_data(ttl=3600)
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
        response.raise_for_status()
        data = response.json()

    except Exception as e:
        return [], f"학교 검색 중 오류가 발생했습니다: {e}"

    if "schoolInfo" not in data:
        return [], "검색 결과가 없습니다."

    try:
        rows = data["schoolInfo"][1]["row"]
    except (KeyError, IndexError):
        return [], "학교 정보를 찾을 수 없습니다."

    result = []

    for row in rows:
        result.append({
            "학교명": row.get("SCHUL_NM", ""),
            "교육청코드": row.get("ATPT_OFCDC_SC_CODE", ""),
            "학교코드": row.get("SD_SCHUL_CODE", ""),
            "지역": row.get("LCTN_SC_NM", "")
        })

    return result, None


# =========================
# 급식 데이터 가져오기
# =========================

@st.cache_data(ttl=1800)
def get_meal_data(
    office_code,
    school_code,
    school_name,
    start_date,
    end_date
):
    params = {
        "KEY": API_KEY,
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
        "MMEAL_SC_CODE": "2",
        "MLSV_FROM_YMD": start_date.strftime("%Y%m%d"),
        "MLSV_TO_YMD": end_date.strftime("%Y%m%d"),
        "pSize": 1000,
        "pIndex": 1
    }

    try:
        response = requests.get(
            MEAL_API,
            params=params,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()

    except Exception:
        return pd.DataFrame()

    if "mealServiceDietInfo" not in data:
        return pd.DataFrame()

    try:
        rows = data["mealServiceDietInfo"][1]["row"]
    except (KeyError, IndexError):
        return pd.DataFrame()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # 필요한 열이 없는 경우
    required_columns = ["MLSV_YMD", "DDISH_NM", "CAL_INFO"]

    for col in required_columns:
        if col not in df.columns:
            df[col] = ""

    df = df[required_columns].copy()

    df["학교명"] = school_name

    # 날짜 변환
    df["날짜"] = pd.to_datetime(
        df["MLSV_YMD"],
        format="%Y%m%d",
        errors="coerce"
    )

    # 칼로리에서 숫자만 추출
    df["칼로리"] = (
        df["CAL_INFO"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.extract(r"(\d+(?:\.\d+)?)")[0]
    )

    df["칼로리"] = pd.to_numeric(
        df["칼로리"],
        errors="coerce"
    )

    df = df.dropna(subset=["날짜", "칼로리"])

    return df[
        ["학교명", "날짜", "칼로리", "DDISH_NM"]
    ].sort_values("날짜")


# =========================
# 사이드바
# =========================

st.sidebar.header("⚙️ 분석 설정")

today = date.today()

default_start = today - timedelta(days=30)

start_date = st.sidebar.date_input(
    "조회 시작일",
    value=default_start
)

end_date = st.sidebar.date_input(
    "조회 종료일",
    value=today
)

if start_date > end_date:
    st.error("조회 시작일이 종료일보다 늦을 수 없습니다.")
    st.stop()


# =========================
# 학교 검색
# =========================

st.sidebar.subheader("🏫 학교 선택")

st.sidebar.write(
    "학교 이름을 검색하면 NEIS에서 실제 학교 코드와 교육청 코드를 가져옵니다."
)

school_search = st.sidebar.text_input(
    "학교 검색",
    placeholder="예: 송탄고등학교"
)

if school_search:
    results, error = search_school(school_search)

    if error:
        st.sidebar.warning(error)
    else:
        options = [
            f'{r["학교명"]} | {r["지역"]} | {r["교육청코드"]} / {r["학교코드"]}'
            for r in results
        ]

        if options:
            selected_search = st.sidebar.selectbox(
                "검색 결과",
                options
            )

            selected_index = options.index(selected_search)
            selected_school = results[selected_index]

            st.sidebar.success(
                f'선택 학교: {selected_school["학교명"]}'
            )

            st.sidebar.caption(
                f'교육청 코드: {selected_school["교육청코드"]}'
            )

            st.sidebar.caption(
                f'학교 코드: {selected_school["학교코드"]}'
            )

            if st.sidebar.button("➕ 비교 학교에 추가"):
                st.session_state.setdefault(
                    "schools",
                    {}
                )

                st.session_state["schools"][
                    selected_school["학교명"]
                ] = selected_school


# =========================
# 기본 학교
# =========================

if "schools" not in st.session_state:
    st.session_state["schools"] = {}

# 송탄고등학교를 기본 학교로 검색
if "송탄고등학교" not in st.session_state["schools"]:

    results, error = search_school("송탄고등학교")

    if not error and results:

        # 정확히 송탄고등학교인 결과 우선
        exact = [
            r for r in results
            if r["학교명"] == "송탄고등학교"
        ]

        if exact:
            st.session_state["schools"]["송탄고등학교"] = exact[0]


# =========================
# 선택 학교 확인
# =========================

school_dict = st.session_state["schools"]

if school_dict:
    school_names = list(school_dict.keys())

    selected_names = st.sidebar.multiselect(
        "비교할 학교",
        options=school_names,
        default=school_names,
        help="3곳 이상의 학교를 선택하면 여러 학교를 동시에 비교할 수 있습니다."
    )
else:
    selected_names = []


# =========================
# 학교 코드 확인 영역
# =========================

with st.expander("🔎 등록된 학교와 실제 API 코드 확인"):

    if school_dict:
        code_df = pd.DataFrame([
            {
                "학교명": name,
                "지역": info["지역"],
                "교육청 코드": info["교육청코드"],
                "학교 코드": info["학교코드"]
            }
            for name, info in school_dict.items()
        ])

        st.dataframe(
            code_df,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.write("등록된 학교가 없습니다.")


# =========================
# 학교 선택 확인
# =========================

if len(selected_names) < 3:
    st.warning(
        "학교를 최소 3곳 선택해 주세요. "
        "송탄고등학교를 포함해 주변 학교를 추가할 수 있습니다."
    )
    st.stop()


# =========================
# 데이터 수집
# =========================

with st.spinner("NEIS에서 급식 데이터를 불러오는 중입니다..."):

    all_data = []

    for school_name in selected_names:

        info = school_dict[school_name]

        df = get_meal_data(
            info["교육청코드"],
            info["학교코드"],
            school_name,
            start_date,
            end_date
        )

        if not df.empty:
            all_data.append(df)


# =========================
# 데이터가 없는 경우
# =========================

if not all_data:
    st.error(
        "선택한 학교들의 급식 데이터를 찾을 수 없습니다. "
        "조회 기간이나 학교 선택을 확인해 주세요."
    )
    st.stop()


df_all = pd.concat(
    all_data,
    ignore_index=True
)


# =========================
# 데이터 개요
# =========================

st.subheader("📊 분석 기간")

st.write(
    f"**{start_date.strftime('%Y년 %m월 %d일')} ~ "
    f"{end_date.strftime('%Y년 %m월 %d일')}**"
)

col1, col2, col3 = st.columns(3)

col1.metric(
    "비교 학교 수",
    f"{df_all['학교명'].nunique()}곳"
)

col2.metric(
    "전체 급식 데이터",
    f"{len(df_all)}건"
)

col3.metric(
    "평균 칼로리",
    f"{df_all['칼로리'].mean():,.0f} kcal"
)


# =========================
# 학교별 통계
# =========================

summary = (
    df_all
    .groupby("학교명")["칼로리"]
    .agg(
        평균_칼로리="mean",
        최고_칼로리="max",
        최저_칼로리="min",
        급식일수="count"
    )
    .reset_index()
)

summary["평균_칼로리"] = summary["평균_칼로리"].round(1)


# =========================
# 그래프 1
# =========================

st.divider()

st.subheader("1️⃣ 학교별 평균 급식 칼로리")

fig_bar = px.bar(
    summary,
    x="학교명",
    y="평균_칼로리",
    text="평균_칼로리",
    labels={
        "학교명": "학교",
        "평균_칼로리": "평균 칼로리 (kcal)"
    },
    title="학교별 평균 급식 칼로리 비교"
)

fig_bar.update_traces(
    texttemplate="%{text:.0f} kcal",
    textposition="outside"
)

fig_bar.update_layout(
    yaxis_title="평균 칼로리 (kcal)",
    xaxis_title="학교"
)

st.plotly_chart(
    fig_bar,
    use_container_width=True
)


# =========================
# 그래프 2
# =========================

st.divider()

st.subheader("2️⃣ 날짜별 급식 칼로리 변화")

fig_line = px.line(
    df_all,
    x="날짜",
    y="칼로리",
    color="학교명",
    markers=True,
    labels={
        "날짜": "급식 날짜",
        "칼로리": "칼로리 (kcal)",
        "학교명": "학교"
    },
    title="학교별 날짜에 따른 급식 칼로리 변화"
)

fig_line.update_layout(
    hovermode="x unified",
    yaxis_title="칼로리 (kcal)",
    xaxis_title="날짜"
)

st.plotly_chart(
    fig_line,
    use_container_width=True
)


# =========================
# 통계표
# =========================

st.divider()

st.subheader("3️⃣ 학교별 급식 칼로리 통계")

display_summary = summary.rename(
    columns={
        "학교명": "학교",
        "평균_칼로리": "평균 칼로리 (kcal)",
        "최고_칼로리": "최고 칼로리 (kcal)",
        "최저_칼로리": "최저 칼로리 (kcal)",
        "급식일수": "급식 데이터 수"
    }
)

st.dataframe(
    display_summary,
    use_container_width=True,
    hide_index=True
)


# =========================
# 탐구 결과 도움말
# =========================

st.divider()

st.subheader("💡 탐구 결과 생각해 보기")

highest_school = summary.loc[
    summary["평균_칼로리"].idxmax(),
    "학교명"
]

lowest_school = summary.loc[
    summary["평균_칼로리"].idxmin(),
    "학교명"
]

difference = (
    summary["평균_칼로리"].max()
    - summary["평균_칼로리"].min()
)

st.write(
    f"선택한 학교 중 평균 급식 칼로리가 가장 높은 학교는 "
    f"**{highest_school}**, 가장 낮은 학교는 **{lowest_school}**입니다."
)

st.write(
    f"두 학교의 평균 칼로리 차이는 약 **{difference:.1f} kcal**입니다."
)

st.caption(
    "※ 이 결과는 선택한 기간에 NEIS에 등록된 중식 칼로리 데이터를 기준으로 계산한 값입니다."
)
# =========================
# 추가 질문 - 요일의 비밀
# =========================

st.divider()

st.subheader("🔍 추가 질문")
st.markdown(
    "**송탄고등학교와 주변 학교의 급식 칼로리는 "
    "요일에 따라 어떤 차이를 보일까?**"
)

# 날짜에서 요일 추출
weekday_order = ["월요일", "화요일", "수요일", "목요일", "금요일"]

df_weekday = df_all.copy()

df_weekday["요일"] = df_weekday["날짜"].dt.dayofweek.map({
    0: "월요일",
    1: "화요일",
    2: "수요일",
    3: "목요일",
    4: "금요일",
    5: "토요일",
    6: "일요일"
})

# 평일만 분석
df_weekday = df_weekday[
    df_weekday["요일"].isin(weekday_order)
]

# 학교별 × 요일별 평균
weekday_summary = (
    df_weekday
    .groupby(["학교명", "요일"])["칼로리"]
    .mean()
    .reset_index()
)

weekday_summary["요일"] = pd.Categorical(
    weekday_summary["요일"],
    categories=weekday_order,
    ordered=True
)

weekday_summary = weekday_summary.sort_values(
    ["학교명", "요일"]
)


# =========================
# 요일별 평균 칼로리 그래프
# =========================

st.subheader("📊 요일별 평균 급식 칼로리")

fig_weekday = px.line(
    weekday_summary,
    x="요일",
    y="칼로리",
    color="학교명",
    markers=True,
    category_orders={
        "요일": weekday_order
    },
    labels={
        "요일": "요일",
        "칼로리": "평균 칼로리 (kcal)",
        "학교명": "학교"
    },
    title="학교별 요일에 따른 평균 급식 칼로리"
)

fig_weekday.update_layout(
    hovermode="x unified",
    xaxis_title="요일",
    yaxis_title="평균 칼로리 (kcal)"
)

st.plotly_chart(
    fig_weekday,
    use_container_width=True
)


# =========================
# 전체 학교의 요일별 평균
# =========================

st.subheader("📈 전체 비교 학교의 요일별 평균")

overall_weekday = (
    df_weekday
    .groupby("요일")["칼로리"]
    .mean()
    .reindex(weekday_order)
    .reset_index()
)

fig_overall = px.bar(
    overall_weekday,
    x="요일",
    y="칼로리",
    text="칼로리",
    category_orders={
        "요일": weekday_order
    },
    labels={
        "요일": "요일",
        "칼로리": "평균 칼로리 (kcal)"
    },
    title="요일별 전체 평균 급식 칼로리"
)

fig_overall.update_traces(
    texttemplate="%{text:.0f} kcal",
    textposition="outside"
)

fig_overall.update_layout(
    xaxis_title="요일",
    yaxis_title="평균 칼로리 (kcal)"
)

st.plotly_chart(
    fig_overall,
    use_container_width=True
)


# =========================
# 가장 높은 / 낮은 요일
# =========================

if not overall_weekday.empty:

    highest_day = overall_weekday.loc[
        overall_weekday["칼로리"].idxmax()
    ]

    lowest_day = overall_weekday.loc[
        overall_weekday["칼로리"].idxmin()
    ]

    col1, col2 = st.columns(2)

    col1.metric(
        "🔥 평균 칼로리가 가장 높은 요일",
        highest_day["요일"],
        f'{highest_day["칼로리"]:.1f} kcal'
    )

    col2.metric(
        "⬇️ 평균 칼로리가 가장 낮은 요일",
        lowest_day["요일"],
        f'{lowest_day["칼로리"]:.1f} kcal'
    )


# =========================
# 학교별 요일 평균 표
# =========================

st.subheader("📋 학교별 요일 평균 칼로리")

weekday_table = weekday_summary.pivot(
    index="학교명",
    columns="요일",
    values="칼로리"
)

weekday_table = weekday_table.reindex(
    columns=weekday_order
)

weekday_table = weekday_table.round(1)

st.dataframe(
    weekday_table,
    use_container_width=True
)
