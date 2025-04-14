import streamlit as st
import pandas as pd
from itertools import permutations

st.title("💘 레이디 이어주기 매칭 분석기")
st.write("구글 폼 데이터를 기반으로 매칭 분석을 합니다.\n'꼭 맞아야 할 조건'이 충족된 경우만 보여줍니다.")

# 👉 구글 시트 공개 CSV 링크 입력
sheet_url = st.text_input("📄 구글 시트 CSV 링크를 입력하세요", 
                          value="https://docs.google.com/spreadsheets/d/e/1FAIpQLSczvU7kKO9JQAr2vDPpzZmVkUgDVgxv-LiL7muxV4RA3HHaBQ/pub?output=csv")

# 🧠 유틸 함수들
def parse_range(text):
    try:
        if '~' in text:
            parts = text.replace(' ', '').split('~')
            if parts[0] == '':
                return float('-inf'), float(parts[1])
            elif parts[1] == '':
                return float(parts[0]), float('inf')
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
        val = float(val)
        return min_val <= val <= max_val
    except:
        return False

def list_overlap(list1, list2):
    return any(item.strip() in [l.strip() for l in list2] for item in list1)

def satisfies_must_conditions(person_a, person_b):
    must_conditions = str(person_a.get("꼭 맞아야 조건들", "")).split(",")
    for cond in must_conditions:
        cond = cond.strip()
        if cond == "거리":
            if not (person_a.get("희망 거리") == person_b.get("희망 거리") or
                    "상관없음" in [person_a.get("희망 거리"), person_b.get("희망 거리")]):
                return False
        elif cond == "키":
            if not is_in_range(person_b.get("레이디 키"), person_a.get("상대방 키 희망")):
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

    if is_in_range(person_a.get("레이디 나이"), person_b.get("선호하는 나이 범위", "")):
        score += 1
    if is_in_range(person_b.get("레이디 나이"), person_a.get("선호하는 나이 범위", "")):
        score += 1

    if is_in_range(person_a.get("레이디 키"), person_b.get("상대방 키 희망")):
        score += 1
    if is_in_range(person_b.get("레이디 키"), person_a.get("상대방 키 희망")):
        score += 1

    if person_a.get("희망 거리") == person_b.get("희망 거리") or "상관없음" in [person_a.get("희망 거리"), person_b.get("희망 거리")]:
        score += 1

    yn_fields = ["흡연", "음주", "타투", "벽장", "퀴어 지인 多"]
    for field in yn_fields:
        if person_a.get(f"{field}(레이디)") == person_b.get(f"{field}(상대방)"):
            score += 1
        if person_b.get(f"{field}(레이디)") == person_a.get(f"{field}(상대방)"):
            score += 1

    detail_fields = ["연락 텀", "머리 길이", "데이트 선호 주기"]
    for field in detail_fields:
        if person_a.get(f"{field}(레이디)") == person_b.get(f"{field}(상대방)"):
            score += 1
        if person_b.get(f"{field}(레이디)") == person_a.get(f"{field}(상대방)"):
            score += 1

    if person_a.get("성격(레이디)") == person_b.get("성격(상대방)"):
        score += 1
    if person_b.get("성격(레이디)") == person_a.get("성격(상대방)"):
        score += 1

    a_levels = str(person_a.get("양금 레벨", "")).split(",")
    b_pref_levels = str(person_b.get("희망 양금 레벨", "")).split(",")
    if list_overlap(a_levels, b_pref_levels):
        score += 1

    return score

def get_filtered_matches(df):
    matches = []
    for a, b in permutations(df.index, 2):
        person_a = df.loc[a]
        person_b = df.loc[b]

        if not satisfies_must_conditions(person_a, person_b):
            continue
        if not satisfies_must_conditions(person_b, person_a):
            continue

        score = match_score(person_a, person_b)
        matches.append({
            "A 닉네임": person_a["닉네임"],
            "B 닉네임": person_b["닉네임"],
            "매칭 점수": score
        })
    return pd.DataFrame(matches).sort_values(by="매칭 점수", ascending=False)

# ✅ 실행
if sheet_url:
    try:
        df = pd.read_csv(sheet_url)
        st.success("✅ 데이터 불러오기 성공!")
        st.dataframe(df)

        result_df = get_filtered_matches(df)
        st.subheader("💘 매칭 결과 (꼭 맞아야 할 조건 만족한 경우만)")
        st.dataframe(result_df)

    except Exception as e:
        st.error(f"⚠️ 오류 발생: {e}")
