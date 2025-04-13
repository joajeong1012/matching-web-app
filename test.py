import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

st.title("매칭 분석기")
st.write("엑셀 데이터를 복사해서 아래에 붙여넣으세요 (열은 Tab 또는 콤마로 구분)")

user_input = st.text_area("여기에 엑셀 데이터를 붙여넣으세요", height=200)

def is_match(val, desired_val):
    """기본적으로 값이 같으면 매칭."""
    return str(val).strip() == str(desired_val).strip()

def is_within_range(val, desired_range):
    """범위 비교: '160-180' 형식의 범위 내에 들어가는지 체크."""
    try:
        if pd.isnull(val) or pd.isnull(desired_range):
            return False
        val = float(val)
        if "-" in str(desired_range):
            min_val, max_val = map(float, desired_range.split("-"))
            return min_val <= val <= max_val
        else:
            return float(desired_range) == val
    except:
        return False

def match_score(person_a, person_b):
    score = 0

    # 쌍방향으로 조건 체크
    for prefix, reverse_prefix in [('나이', '원하는 나이'), ('키', '원하는 키'), ('거리', '원하는 거리')]:
        if is_within_range(person_a.get(prefix), person_b.get(f'원하는 {prefix}')):
            score += 1
        if is_within_range(person_b.get(prefix), person_a.get(f'원하는 {prefix}')):
            score += 1

    # 단순 일치 비교 항목들 (이진형, 텍스트형 등)
    simple_fields = [
        ('흡연 여부', '상대방의 흡연 여부'),
        ('음주 여부', '상대방의 음주 여부'),
        ('연락 텀', '상대방의 연락 텀'),
        ('머리길이', '상대방의 머리길이'),
        ('성격', '상대방의 성격'),
    ]

    for my_field, desired_field in simple_fields:
        if is_match(person_a.get(my_field), person_b.get(desired_field)):
            score += 1
        if is_match(person_b.get(my_field), person_a.get(desired_field)):
            score += 1

    return score

def get_matches(df):
    matches = []
    for a, b in permutations(df.index, 2):
        score = match_score(df.loc[a], df.loc[b])
        matches.append({
            "A": df.loc[a, '닉네임'],
            "B": df.loc[b, '닉네임'],
            "매칭 점수": score
        })
    return pd.DataFrame(matches).sort_values(by="매칭 점수", ascending=False)

if user_input:
    try:
        df = pd.read_csv(StringIO(user_input), sep=None, engine="python")
        st.success("✅ 데이터 분석 성공!")
        st.dataframe(df)

        result_df = get_matches(df)
        st.subheader("💡 매칭 결과")
        st.dataframe(result_df)

    except Exception as e:
        st.error(f"⚠️ 데이터 분석 실패: {e}")
