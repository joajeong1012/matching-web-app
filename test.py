import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

st.title("💘 레이디 이어주기 매칭 분석기")
st.write("📋 구글 폼 응답을 복사해서 붙여넣어주세요 (열은 탭으로 구분됩니다).")

user_input = st.text_area("📥 여기에 데이터를 붙여넣으세요", height=300)

expected_columns = [
    "응답 시간",  # 무시
    "닉네임",
    "레이디 나이",
    "선호하는 상대방 레이디 나이",
    "레이디의 거주 지역",
    "희망하는 거리 조건",
    "레이디 키",
    "상대방 레이디 키",
    "흡연(레이디)",
    "흡연(상대방)",
    "음주(레이디)",
    "음주(상대방)",
    "타투(레이디)",
    "타투(상대방)",
    "벽장(레이디)",
    "벽장(상대방)",
    "퀴어 지인 多(레이디)",
    "퀴어 지인 多(상대방)",
    "성격(레이디)",
    "성격(상대방)",
    "연락 텀(레이디)",
    "연락 텀(상대방)",
    "머리 길이(레이디)",
    "머리 길이(상대방)",
    "데이트 선호 주기",
    "손톱길이(농담)",
    "양금 레벨",
    "희망 양금 레벨",
    "연애 텀",  # 무시
    "꼭 맞아야 조건들",
    "더 추가하고 싶으신 이상언니(형)과 레이디 소개 간단하게 적어주세요!!"
]

def parse_range(text):
    try:
        if '~' in text:
            parts = text.replace(' ', '').split('~')
            return float(parts[0]), float(parts[1])
        else:
            val = float(text)
            return val, val
    except:
        return None, None

def is_in_range(val, range_text):
    try:
        if pd.isnull(val) or pd.isnull(range_text):
            return False
        min_val, max_val = parse_range(range_text)
        return min_val <= float(val) <= max_val
    except:
        return False

def is_in_range_list(val, range_texts):
    try:
        ranges = str(range_texts).split(",")
        return any(is_in_range(val, r.strip()) for r in ranges)
    except:
        return False

def list_overlap(list1, list2):
    return any(item.strip() in [l.strip() for l in list2] for item in list1)

def satisfies_must_conditions(person_a, person_b):
    must_conditions = str(person_a.get("꼭 맞아야 조건들", "")).split(",")
    for cond in must_conditions:
        cond = cond.strip()
        if cond == "거리":
            if (person_a.get("희망하는 거리 조건") == "단거리" or person_b.get("희망하는 거리 조건") == "단거리"):
                if person_a.get("레이디의 거주 지역") != person_b.get("레이디의 거주 지역"):
                    return False
        elif cond == "키":
            if not is_in_range(person_b.get("레이디 키"), person_a.get("상대방 레이디 키")):
                return False
        elif cond == "흡연":
            if person_b.get("흡연(레이디)") != person_a.get("흡연(상대방)"):
                return False
        elif cond == "음주":
            if person_b.get("음주(레이디)") != person_a.get("음주(상대방)"):
                return False
        elif cond == "타투":
            if person_b.get("타투(레이디)") != person_a.get("타투(상대방)"):
                return False
        elif cond == "벽장":
            if person_b.get("벽장(레이디)") != person_a.get("벽장(상대방)"):
                return False
        elif cond == "성격":
            if person_b.get("성격(레이디)") != person_a.get("성격(상대방)"):
                return False
        elif cond == "연락 텀":
            if person_b.get("연락 텀(레이디)") != person_a.get("연락 텀(상대방)"):
                return False
        elif cond == "머리 길이":
            if person_b.get("머리 길이(레이디)") != person_a.get("머리 길이(상대방)"):
                return False
        elif cond == "데이트 주기":
            if person_b.get("데이트 선호 주기") != person_a.get("데이트 선호 주기"):
                return False
        elif cond == "퀴어 지인 多":
            if person_b.get("퀴어 지인 多(레이디)") != person_a.get("퀴어 지인 多(상대방)"):
                return False
        elif cond == "앙큼 레벨":
            a_levels = str(person_a.get("희망 양금 레벨", "")).split(",")
            b_levels = str(person_b.get("양금 레벨", "")).split(",")
            if not list_overlap(a_levels, b_levels):
                return False
    return True

def match_score(person_a, person_b):
    score = 0
    total = 0

    if is_in_range_list(person_a.get("레이디 나이"), person_b.get("선호하는 상대방 레이디 나이")):
        score += 1
    total += 1
    if is_in_range_list(person_b.get("레이디 나이"), person_a.get("선호하는 상대방 레이디 나이")):
        score += 1
    total += 1

    if is_in_range(person_a.get("레이디 키"), person_b.get("상대방 레이디 키")):
        score += 1
    total += 1
    if is_in_range(person_b.get("레이디 키"), person_a.get("상대방 레이디 키")):
        score += 1
    total += 1

    distance_match = False
    if person_a.get("희망하는 거리 조건") == "단거리" or person_b.get("희망하는 거리 조건") == "단거리":
        if person_a.get("레이디의 거주 지역") == person_b.get("레이디의 거주 지역"):
            distance_match = True
    else:
        distance_match = True

    if distance_match:
        score += 1
    total += 1

    yn_fields = ["흡연", "음주", "타투", "벽장", "퀴어 지인 多"]
    for field in yn_fields:
        if person_a.get(f"{field}(레이디)") == person_b.get(f"{field}(상대방)"):
            score += 1
        total += 1
        if person_b.get(f"{field}(레이디)") == person_a.get(f"{field}(상대방)"):
            score += 1
        total += 1

    detail_fields = ["연락 텀", "머리 길이", "데이트 선호 주기"]
    for field in detail_fields:
        if person_a.get(f"{field}(레이디)") == person_b.get(f"{field}(상대방)"):
            score += 1
        total += 1
        if person_b.get(f"{field}(레이디)") == person_a.get(f"{field}(상대방)"):
            score += 1
        total += 1

    if person_a.get("성격(레이디)") == person_b.get("성격(상대방)"):
        score += 1
    total += 1
    if person_b.get("성격(레이디)") == person_a.get("성격(상대방)"):
        score += 1
    total += 1

    a_levels = str(person_a.get("양금 레벨", "")).split(",")
    b_pref_levels = str(person_b.get("희망 양금 레벨", "")).split(",")
    if list_overlap(a_levels, b_pref_levels):
        score += 1
    total += 1

    return score, total

def get_filtered_matches(df):
    matches = []
    seen_pairs = set()

    for a, b in permutations(df.index, 2):
        person_a = df.loc[a]
        person_b = df.loc[b]

        pair_key = tuple(sorted([person_a["닉네임"], person_b["닉네임"]]))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        if not satisfies_must_conditions(person_a, person_b):
            continue
        if not satisfies_must_conditions(person_b, person_a):
            continue

        score, total = match_score(person_a, person_b)
        percent = round(score / total * 100, 1)
        summary = f"{score} / {total}점 ({percent}%)"

        matches.append({
            "A 닉네임": pair_key[0],
            "B 닉네임": pair_key[1],
            "매칭 점수": score,
            "총 점수": total,
            "비율 (%)": percent,
            "결과 요약": summary
        })

    return pd.DataFrame(matches).sort_values(by="매칭 점수", ascending=False)

# 실행
if user_input:
    try:
        df = pd.read_csv(StringIO(user_input), sep="\t", header=None)
        df.columns = expected_columns

        df = df.drop(columns=["응답 시간", "손톱길이(농담)", "연애 텀",
                              "더 추가하고 싶으신 이상언니(형)과 레이디 소개 간단하게 적어주세요!!"])

        st.success("✅ 데이터 분석 성공!")
        st.dataframe(df)

        result_df = get_filtered_matches(df)

        if result_df.empty:
            st.warning("⚠️ '꼭 맞아야 할 조건'을 모두 만족하는 매칭 결과가 없습니다.")
        else:
            st.subheader("💘 매칭 결과")
            st.dataframe(result_df)

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
