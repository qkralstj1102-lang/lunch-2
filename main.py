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
