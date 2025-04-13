import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO

st.title("매칭 분석기")
st.write("엑셀 데이터를 복사해서 아래에 붙여넣으세요 (열은 Tab 또는 콤마로 구분)")

user_input = st.text_area("여기에 엑셀 데이터를 붙여넣으세요", height=200)

def match_score(person_a, person_b):
    actual = person_a[['성향1', '성향2', '성향3']].values.astype(float)
    desired = person_b[['원하는_성향1', '원하는_성향2', '원하는_성향3']].values.astype(float)
    distance = np.linalg.norm(actual - desired)
    return 100 - distance

def get_matches(df):
    from itertools import permutations
    matches = []
    for a, b in permutations(df.index, 2):
        score = match_score(df.loc[a], df.loc[b])
        matches.append({
            "A": df.loc[a, '이름'],
            "B": df.loc[b, '이름'],
            "매칭 점수": round(score, 2)
        })
    return pd.DataFrame(matches).sort_values(by="매칭 점수", ascending=False)

if user_input:
    try:
        # 복사된 데이터 파싱 (탭 or 쉼표 자동 구분)
        df = pd.read_csv(StringIO(user_input), sep=None, engine="python")
        st.success("✅ 데이터 분석 성공!")
        st.dataframe(df)

        result_df = get_matches(df)
        st.subheader("💡 매칭 결과")
        st.dataframe(result_df)

    except Exception as e:
        st.error(f"⚠️ 데이터 분석 실패: {e}")
