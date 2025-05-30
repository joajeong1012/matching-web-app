import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

# ===================== UI 설정 ============================
st.set_page_config(page_title="레이디 매칭 분석기", layout="wide")

st.title("💘 레이디 이어주기 매칭 분석기 2.0")
st.markdown("#### 📋 구글 폼 응답을 복사해서 붙여넣어주세요 (TSV 형식)")
st.markdown("양식: 탭으로 구분된 데이터. 전체 응답 복사 → 붙여넣기")

user_input = st.text_area("📥 응답 데이터를 붙여넣으세요", height=300)

# ===================== 유틸 함수 ============================
def parse_range(text):
    try:
        if pd.isna(text): return None, None
        text = str(text).strip()
        if not text or text == "~": return None, None
        if '~' in text:
            parts = text.replace(' ', '').split('~')
            return float(parts[0]), float(parts[1]) if len(parts) == 2 else (None, None)
        else:
            return float(text), float(text)
    except:
        return None, None

def is_in_range(val, range_text):
    try:
        val = float(val)
        min_val, max_val = parse_range(range_text)
        if min_val is None or max_val is None:
            return False
        return min_val <= val <= max_val
    except:
        return False

def is_in_range_list(val, range_texts):
    return any(is_in_range(val, r.strip()) for r in str(range_texts).split(",") if r.strip())

def list_overlap(list1, list2):
    return any(a.strip() in [b.strip() for b in list2] for a in list1 if a.strip())

def is_preference_match(preference_value, target_value):
    if pd.isna(preference_value) or pd.isna(target_value):
        return False
    pref_list = [x.strip() for x in str(preference_value).split(",")]
    return "상관없음" in pref_list or str(target_value).strip() in pref_list

# ===================== 조건 비교 ============================
def satisfies_must_conditions(person_a, person_b):
    musts = str(person_a.get("꼭 맞아야 조건들", "")).split(",")
    for cond in musts:
        cond = cond.strip()
        if cond == "거리" and person_a["희망하는 거리 조건"] == "단거리":
            if person_a["레이디의 거주 지역"] != person_b["레이디의 거주 지역"]:
                return False
        elif cond == "성격":
            if not is_preference_match(person_a["성격(상대방)"], person_b["성격(레이디)"]):
                return False
        elif cond == "머리 길이":
            if not is_preference_match(person_a["머리 길이(상대방)"], person_b["머리 길이(레이디)"]):
                return False
        elif cond == "앙큼 레벨":
            if not list_overlap(
                str(person_a["희망 양금 레벨"]).split(","),
                str(person_b["양금 레벨"]).split(",")
            ):
                return False
    return True

# ===================== 매칭 점수 계산 ============================
def match_score(a, b):
    score, total = 0, 0
    matched = []

    # 나이
    if is_in_range_list(a["레이디 나이"], b["선호하는 상대방 레이디 나이"]):
        score += 2
        matched.append("A 나이 → B 선호")
    total += 1
    if is_in_range_list(b["레이디 나이"], a["선호하는 상대방 레이디 나이"]):
        score += 2
        matched.append("B 나이 → A 선호")
    total += 1

    # 키
    if is_in_range(a["레이디 키"], b["상대방 레이디 키"]):
        score += 1
        matched.append("A 키 → B 선호")
    total += 1
    if is_in_range(b["레이디 키"], a["상대방 레이디 키"]):
        score += 1
        matched.append("B 키 → A 선호")
    total += 1

    # 거리
    if a["희망하는 거리 조건"] == "단거리" or b["희망하는 거리 조건"] == "단거리":
        if a["레이디의 거주 지역"] == b["레이디의 거주 지역"]:
            score += 1
            matched.append("거리 일치 (단거리)")
        total += 1
    else:
        score += 1
        matched.append("거리 무관")
        total += 1

    # 기타 항목
    for field in ["흡연", "음주", "타투", "벽장", "퀴어 지인 多"]:
        a_self, a_wish = a[f"{field}(레이디)"], b[f"{field}(상대방)"]
        b_self, b_wish = b[f"{field}(레이디)"], a[f"{field}(상대방)"]

        if is_preference_match(a_wish, a_self):
            score += 1
            matched.append(f"A {field}")
        total += 1
        if is_preference_match(b_wish, b_self):
            score += 1
            matched.append(f"B {field}")
        total += 1

    for field in ["연락 텀", "머리 길이", "데이트 선호 주기"]:
        r, d = field + "(레이디)", field + "(상대방)"
        if is_preference_match(b[d], a[r]):
            score += 1
            matched.append(f"A {field}")
        total += 1
        if is_preference_match(a[d], b[r]):
            score += 1
            matched.append(f"B {field}")
        total += 1

    # 성격
    if is_preference_match(b["성격(상대방)"], a["성격(레이디)"]):
        score += 1
        matched.append("A 성격")
    total += 1
    if is_preference_match(a["성격(상대방)"], b["성격(레이디)"]):
        score += 1
        matched.append("B 성격")
    total += 1

    # 앙금 레벨
    if list_overlap(str(a["양금 레벨"]).split(","), str(b["희망 양금 레벨"]).split(",")):
        score += 1
        matched.append("앙금 레벨")
    total += 1

    return score, total, matched

# ===================== 실행 ============================
if user_input:
    try:
        raw_df = pd.read_csv(StringIO(user_input), sep="\t")

        df = pd.DataFrame({
            "닉네임": raw_df.iloc[:, 1],
            "레이디 나이": raw_df.iloc[:, 2],
            "선호하는 상대방 레이디 나이": raw_df.iloc[:, 3],
            "레이디의 거주 지역": raw_df.iloc[:, 4],
            "희망하는 거리 조건": raw_df.iloc[:, 5],
            "레이디 키": pd.to_numeric(raw_df.iloc[:, 6], errors="coerce"),
            "상대방 레이디 키": raw_df.iloc[:, 7],
            "흡연(레이디)": raw_df.iloc[:, 8],
            "흡연(상대방)": raw_df.iloc[:, 9],
            "음주(레이디)": raw_df.iloc[:, 10],
            "음주(상대방)": raw_df.iloc[:, 11],
            "타투(레이디)": raw_df.iloc[:, 12],
            "타투(상대방)": raw_df.iloc[:, 13],
            "벽장(레이디)": raw_df.iloc[:, 14],
            "벽장(상대방)": raw_df.iloc[:, 15],
            "성격(레이디)": raw_df.iloc[:, 16],
            "성격(상대방)": raw_df.iloc[:, 17],
            "연락 텀(레이디)": raw_df.iloc[:, 18],
            "연락 텀(상대방)": raw_df.iloc[:, 19],
            "머리 길이(레이디)": raw_df.iloc[:, 20],
            "머리 길이(상대방)": raw_df.iloc[:, 21],
            "데이트 선호 주기(레이디)": raw_df.iloc[:, 22],
            "퀴어 지인 多(레이디)": raw_df.iloc[:, 25],
            "퀴어 지인 多(상대방)": raw_df.iloc[:, 26],
            "양금 레벨": raw_df.iloc[:, 27],
            "희망 양금 레벨": raw_df.iloc[:, 28],
            "손톱길이(농담)": raw_df.iloc[:, 29],
            "꼭 맞아야 조건들": raw_df.iloc[:, 30]
        })

        st.success("✅ 데이터 분석 성공!")
        with st.expander("🔍 입력 데이터 보기"):
            st.dataframe(df)

        matches = []
        seen = set()
        for a, b in permutations(df.index, 2):
            pa, pb = df.loc[a], df.loc[b]
            pair = tuple(sorted([pa["닉네임"], pb["닉네임"]]))
            if pair in seen: continue
            seen.add(pair)
            if not satisfies_must_conditions(pa, pb) or not satisfies_must_conditions(pb, pa):
                continue
            s, t, conds = match_score(pa, pb)
            percent = round((s / t) * 100, 1)
            matches.append({
                "A 닉네임": pair[0],
                "B 닉네임": pair[1],
                "매칭 점수": s,
                "총 점수": t,
                "비율(%)": percent,
                "요약": f"{s} / {t}점 ({percent}%)",
                "일치 조건들": ", ".join(conds)
            })

        result_df = pd.DataFrame(matches).sort_values(by="매칭 점수", ascending=False)
        st.subheader("💘 매칭 결과")
        if result_df.empty:
            st.warning("😢 매칭 조건을 만족하는 결과가 없습니다.")
        else:
            st.dataframe(result_df)

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
