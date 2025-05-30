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
def clean_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.dropna(axis=1, how="all")
    df = df.loc[:, ~df.columns.duplicated()]
    df.columns = df.columns.str.strip().str.replace(r"\s+", " ", regex=True)

    # ── 긴 제목 → 표준 이름 ──
    pattern_map = {
        "닉네임":        "닉네임",
        "레이디 나이":   "레이디 나이",
        "선호하는 상대방 레이디 나이": "선호하는 상대방 레이디 나이",
        "레이디 키":     "레이디 키",
        "상대방 레이디 키": "상대방 레이디 키",
        "레이디의 거주 지역": "레이디의 거주 지역",
        "희망하는 거리 조건": "희망하는 거리 조건",
        "데이트 선호 주기": "데이트 선호 주기(레이디)",
    }
    for patt, std in pattern_map.items():
        hits = [c for c in df.columns if patt in c]
        if hits:
            df = df.rename(columns={hits[0]: std})

    # 수치형 변환
    for col in ["레이디 키", "레이디 나이"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # (레이디)/(상대방) 계열 기본값
    counterpart = [
        "흡연", "음주", "타투", "벽장", "퀴어 지인 多",
        "연락 텀", "머리 길이", "데이트 선호 주기",
        "성격"
    ]
    for base in counterpart:
        for suffix in ["(레이디)", "(상대방)"]:
            col = f"{base}{suffix}"
            if col not in df.columns:
                df[col] = "상관없음"

    # 누락 방지
    for key in ["양금 레벨", "희망 양금 레벨", "꼭 맞아야 조건들"]:
        if key not in df.columns:
            df[key] = ""

    return df

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

def satisfies_must_conditions(person_a, person_b):
    musts = str(person_a.get("꼭 맞아야 조건들", "")).split(",")
    for cond in musts:
        cond = cond.strip()
        if cond == "거리" and person_a["희망하는 거리 조건"] == "단거리":
            if person_a["레이디의 거주 지역"] != person_b["레이디의 거주 지역"]:
                return False
        elif cond == "성격":
            if not is_preference_match(person_a.get("성격(상대방)", "상관없음"), person_b.get("성격(레이디)", "상관없음")):
                return False
        elif cond == "머리 길이":
            if not is_preference_match(person_a.get("머리 길이(상대방)", "상관없음"), person_b.get("머리 길이(레이디)", "상관없음")):
                return False
        elif cond == "앙큼 레벨":
            if not list_overlap(
                str(person_a.get("희망 양금 레벨", "")).split(","),
                str(person_b.get("양금 레벨", "")).split(",")
            ):
                return False
    return True

def match_score(a, b):
    score, total = 0, 0
    matched = []

    if is_in_range_list(a["레이디 나이"], b["선호하는 상대방 레이디 나이"]):
        score += 2; matched.append("A 나이 → B 선호")
    total += 1
    if is_in_range_list(b["레이디 나이"], a["선호하는 상대방 레이디 나이"]):
        score += 2; matched.append("B 나이 → A 선호")
    total += 1

    if is_in_range(a["레이디 키"], b["상대방 레이디 키"]):
        score += 1; matched.append("A 키 → B 선호")
    total += 1
    if is_in_range(b["레이디 키"], a["상대방 레이디 키"]):
        score += 1; matched.append("B 키 → A 선호")
    total += 1

    if a["희망하는 거리 조건"] == "단거리" or b["희망하는 거리 조건"] == "단거리":
        if a["레이디의 거주 지역"] == b["레이디의 거주 지역"]:
            score += 1; matched.append("거리 일치 (단거리)")
        total += 1
    else:
        score += 1; matched.append("거리 무관")
        total += 1

    for base in ["흡연", "음주", "타투", "벽장", "퀴어 지인 多"]:
        a_self = a.get(f"{base}(레이디)", "상관없음")
        a_pref = b.get(f"{base}(상대방)", "상관없음")
        b_self = b.get(f"{base}(레이디)", "상관없음")
        b_pref = a.get(f"{base}(상대방)", "상관없음")

        if is_preference_match(a_pref, a_self):
            score += 1; matched.append(f"A {base}")
        total += 1
        if is_preference_match(b_pref, b_self):
            score += 1; matched.append(f"B {base}")
        total += 1

    for base in ["연락 텀", "머리 길이", "데이트 선호 주기"]:
        a_self = a.get(f"{base}(레이디)", "상관없음")
        a_pref = b.get(f"{base}(상대방)", "상관없음")
        b_self = b.get(f"{base}(레이디)", "상관없음")
        b_pref = a.get(f"{base}(상대방)", "상관없음")

        if is_preference_match(a_pref, a_self):
            score += 1; matched.append(f"A {base}")
        total += 1
        if is_preference_match(b_pref, b_self):
            score += 1; matched.append(f"B {base}")
        total += 1

    if is_preference_match(b.get("성격(상대방)", "상관없음"), a.get("성격(레이디)", "상관없음")):
        score += 1; matched.append("A 성격")
    total += 1
    if is_preference_match(a.get("성격(상대방)", "상관없음"), b.get("성격(레이디)", "상관없음")):
        score += 1; matched.append("B 성격")
    total += 1

    if list_overlap(str(a.get("양금 레벨", "")).split(","), str(b.get("희망 양금 레벨", "")).split(",")):
        score += 1; matched.append("앙금 레벨")
    total += 1

    return score, total, matched

# ===================== 실행 ============================
if user_input:
    try:
        raw_df = pd.read_csv(StringIO(user_input), sep="\t")
        df = clean_df(raw_df)

        st.success("✅ 데이터 정제 완료!")
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
