import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations
import re

st.title("💘 레이디 이어주기 매칭 분석기")
st.write("📋 구글 폼 응답을 복사해서 붙여넣어주세요 (탭으로 구분된 데이터 형식)")

user_input = st.text_area("📥 데이터를 붙여넣으세요", height=300)

# ▶ 예상되는 열 이름
expected_columns = [
    "응답 시간", "닉네임", "레이디 나이", "선호하는 상대방 레이디 나이", "레이디의 거주 지역", "희망하는 거리 조건",
    "레이디 키", "상대방 레이디 키", "흡연(레이디)", "흡연(상대방)", "음주(레이디)", "음주(상대방)",
    "타투(레이디)", "타투(상대방)", "벽장(레이디)", "벽장(상대방)", "퀴어 지인 多(레이디)", "퀴어 지인 多(상대방)",
    "성격(레이디)", "성격(상대방)", "연락 텀(레이디)", "연락 텀(상대방)", "머리 길이(레이디)", "머리 길이(상대방)",
    "데이트 선호 주기", "손톱길이(농담)", "양금 레벨", "", "희망 양금 레벨", "연애 텀", "꼭 맞아야 조건들",
    "더 추가하고 싶으신 이상언니(형)과 레이디 소개 간단하게 적어주세요!!"
]

def clean_df(raw_df):
    df = raw_df.dropna(axis=1, how="all")  # 전부 NaN 열 제거
    df = df.loc[:, ~df.columns.duplicated()]  # 중복 열 제거
    df = df.iloc[:, :32]  # 최대 32열만 유지
    df.columns = expected_columns[:32]
    return df.drop(columns=[
        "응답 시간", "손톱길이(농담)", "연애 텀", "더 추가하고 싶으신 이상언니(형)과 레이디 소개 간단하게 적어주세요!!"
    ], errors="ignore")

def parse_range(text):
    try:
        if '~' in text:
            parts = text.replace(' ', '').split('~')
            return float(parts[0]), float(parts[1])
        else:
            return float(text), float(text)
    except:
        return None, None

def is_in_range(val, range_text):
    try:
        min_val, max_val = parse_range(range_text)
        return min_val <= float(val) <= max_val
    except:
        return False

def is_in_range_list(val, range_texts):
    try:
        ranges = str(range_texts).split(",")
        return any(is_in_range(val, r.strip()) for r in ranges if r.strip())
    except:
        return False

def list_overlap(list1, list2):
    return any(a.strip() in [b.strip() for b in list2] for a in list1 if a.strip())

def satisfies_must_conditions(person_a, person_b):
    musts = str(person_a.get("꼭 맞아야 조건들", "")).split(",")
    for cond in musts:
        cond = cond.strip()
        if cond == "거리":
            if (person_a.get("희망하는 거리 조건") == "단거리" or person_b.get("희망하는 거리 조건") == "단거리"):
                if person_a.get("레이디의 거주 지역") != person_b.get("레이디의 거주 지역"):
                    return False
        elif cond == "머리 길이":
            if person_b.get("머리 길이(레이디)") != person_a.get("머리 길이(상대방)"):
                return False
        elif cond == "성격":
            if person_b.get("성격(레이디)") != person_a.get("성격(상대방)"):
                return False
        elif cond == "앙큼 레벨":
            a_levels = str(person_a.get("희망 양금 레벨", "")).split(",")
            b_levels = str(person_b.get("양금 레벨", "")).split(",")
            if not list_overlap(a_levels, b_levels):
                return False
    return True

def match_score(a, b):
    score, total = 0, 0

    if is_in_range_list(a["레이디 나이"], b["선호하는 상대방 레이디 나이"]): score += 1
    total += 1
    if is_in_range_list(b["레이디 나이"], a["선호하는 상대방 레이디 나이"]): score += 1
    total += 1

    if is_in_range(a["레이디 키"], b["상대방 레이디 키"]): score += 1
    total += 1
    if is_in_range(b["레이디 키"], a["상대방 레이디 키"]): score += 1
    total += 1

    # 거리 조건
    if (a["희망하는 거리 조건"] == "단거리" or b["희망하는 거리 조건"] == "단거리"):
        if a["레이디의 거주 지역"] == b["레이디의 거주 지역"]: score += 1
    else:
        score += 1
    total += 1

    for field in ["흡연", "음주", "타투", "벽장", "퀴어 지인 多"]:
        if a[f"{field}(레이디)"] == b[f"{field}(상대방)"]: score += 1
        total += 1
        if b[f"{field}(레이디)"] == a[f"{field}(상대방)"]: score += 1
        total += 1

    for field in ["연락 텀", "머리 길이", "데이트 선호 주기"]:
        if a[f"{field}(레이디)"] == b[f"{field}(상대방)"]: score += 1
        total += 1
        if b[f"{field}(레이디)"] == a[f"{field}(상대방)"]: score += 1
        total += 1

    if a["성격(레이디)"] == b["성격(상대방)"]: score += 1
    total += 1
    if b["성격(레이디)"] == a["성격(상대방)"]: score += 1
    total += 1

    if list_overlap(str(a["양금 레벨"]).split(","), str(b["희망 양금 레벨"]).split(",")): score += 1
    total += 1

    return score, total

def get_matches(df):
    matches, seen = [], set()
    for a, b in permutations(df.index, 2):
        pa, pb = df.loc[a], df.loc[b]
        pair_key = tuple(sorted([pa["닉네임"], pb["닉네임"]]))
        if pair_key in seen:
            continue
        seen.add(pair_key)

        if not satisfies_must_conditions(pa, pb): continue
        if not satisfies_must_conditions(pb, pa): continue

        s, t = match_score(pa, pb)
        percent = round((s / t) * 100, 1)
        matches.append({
            "A 닉네임": pair_key[0],
            "B 닉네임": pair_key[1],
            "매칭 점수": s,
            "총 점수": t,
            "비율(%)": percent,
            "요약": f"{s} / {t}점 ({percent}%)"
        })
    return pd.DataFrame(matches).sort_values(by="매칭 점수", ascending=False)

# 🔄 실행
if user_input:
    try:
        df = pd.read_csv(StringIO(user_input), sep="\t", header=None)
        df = clean_columns(df)
        st.success("✅ 데이터 분석 성공!")
        st.dataframe(df)

        result = get_matches(df)

        if result.empty:
            st.warning("❗ 매칭 조건을 만족하는 결과가 없습니다.")
        else:
            st.subheader("💘 매칭 결과")
            st.dataframe(result)

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
