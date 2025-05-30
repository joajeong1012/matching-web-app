# lady_matching_app.py
# ──────────────────────────────────────────────────────────────
# Streamlit 앱: 레이디 이어주기 매칭 분석기 2.0
# 붙여넣은 TSV 데이터를 정제 → 조건 비교 → 매칭 결과 출력
# ──────────────────────────────────────────────────────────────
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

# ===================== 정제 함수 ==========================
def clean_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.dropna(axis=1, how="all")
    df = df.loc[:, ~df.columns.duplicated()]
    df.columns = df.columns.str.strip().str.replace(r"\s+", " ", regex=True)

    # 긴 열 제목 → 표준 이름
    rename_map = {"데이트 선호 주기": "데이트 선호 주기(레이디)"}
    keywords = {
        "닉네임": "닉네임",
        "레이디 나이": "레이디 나이",
        "선호하는 상대방 레이디 나이": "선호하는 상대방 레이디 나이",
        "레이디 키": "레이디 키",
        "상대방 레이디 키": "상대방 레이디 키",
        "레이디의 거주 지역": "레이디의 거주 지역",
        "희망하는 거리 조건": "희망하는 거리 조건",
    }
    for std, kw in keywords.items():
        if std not in df.columns:
            hit = [c for c in df.columns if kw in c]
            if hit:
                rename_map[hit[0]] = std
    df = df.rename(columns=rename_map)

    # 숫자형 변환
    for col in ["레이디 키", "레이디 나이"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 빠질 수 있는 (상대방) 열 기본값
    counterpart_cols = [
        "데이트 선호 주기(상대방)", "연락 텀(상대방)", "머리 길이(상대방)",
        "흡연(상대방)", "음주(상대방)", "타투(상대방)",
        "벽장(상대방)", "퀴어 지인 多(상대방)"
    ]
    for c in counterpart_cols:
        if c not in df.columns:
            df[c] = "상관없음"

    drop_cols = [
        "응답 시간", "손톱길이(농담)", "연애 텀", "",
        "더 추가하고 싶으신 이상언니(형)과 레이디 소개 간단하게 적어주세요!!"
    ]
    return df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

# ===================== 범위/일치 함수 =====================
def parse_range(text):
    try:
        if pd.isna(text): return (None, None)
        text = str(text).strip()
        if not text or text == "~": return (None, None)
        if "~" in text:
            a, b = text.replace(" ", "").split("~")
            return (float(a), float(b))
        return (float(text), float(text))
    except:
        return (None, None)

def is_in_range(val, range_text):
    try:
        val = float(val)
        low, high = parse_range(range_text)
        return low is not None and low <= val <= high
    except:
        return False

def is_in_range_list(val, range_texts):
    return any(is_in_range(val, r.strip()) for r in str(range_texts).split(",") if r.strip())

def list_overlap(list1, list2):
    list2_stripped = [y.strip() for y in list2]
    return any(x.strip() in list2_stripped for x in list1 if x.strip())

def is_preference_match(pref_value, target_value):
    if pd.isna(pref_value) or pd.isna(target_value): return False
    prefs = [x.strip() for x in str(pref_value).split(",")]
    return "상관없음" in prefs or str(target_value).strip() in prefs

# ===================== 필수조건 체크 ======================
def satisfies_must(a, b):
    musts = str(a.get("꼭 맞아야 조건들", "")).split(",")
    for cond in map(str.strip, musts):
        if cond == "거리" and a.get("희망하는 거리 조건") == "단거리":
            if a.get("레이디의 거주 지역") != b.get("레이디의 거주 지역"):
                return False
        elif cond == "성격":
            if not is_preference_match(a.get("성격(상대방)"), b.get("성격(레이디)")):
                return False
        elif cond == "머리 길이":
            if not is_preference_match(a.get("머리 길이(상대방)"), b.get("머리 길이(레이디)")):
                return False
        elif cond == "앙큼 레벨":
            if not list_overlap(
                str(a.get("희망 양금 레벨", "")).split(","),
                str(b.get("양금 레벨", "")).split(",")
            ): return False
    return True

# ===================== 매칭 점수 계산 =====================
def match_score(a, b):
    score, total, matched = 0, 0, []

    # 나이
    if is_in_range_list(a.get("레이디 나이"), b.get("선호하는 상대방 레이디 나이")):
        score += 2; matched.append("A 나이→B 선호")
    total += 1
    if is_in_range_list(b.get("레이디 나이"), a.get("선호하는 상대방 레이디 나이")):
        score += 2; matched.append("B 나이→A 선호")
    total += 1

    # 키
    if is_in_range(a.get("레이디 키"), b.get("상대방 레이디 키")):
        score += 1; matched.append("A 키→B 선호")
    total += 1
    if is_in_range(b.get("레이디 키"), a.get("상대방 레이디 키")):
        score += 1; matched.append("B 키→A 선호")
    total += 1

    # 거리
    if a.get("희망하는 거리 조건") == "단거리" or b.get("희망하는 거리 조건") == "단거리":
        if a.get("레이디의 거주 지역") == b.get("레이디의 거주 지역"):
            score += 1; matched.append("거리 일치(단거리)")
        total += 1
    else:
        score += 1; matched.append("거리 무관")
        total += 1

    # 흡연·음주·타투·벽장·퀴어
    for field in ["흡연", "음주", "타투", "벽장", "퀴어 지인 多"]:
        a_self, a_pref = a.get(f"{field}(레이디)"), b.get(f"{field}(상대방)")
        b_self, b_pref = b.get(f"{field}(레이디)"), a.get(f"{field}(상대방)")
        if is_preference_match(a_pref, a_self):
            score += 1; matched.append(f"A {field}")
        total += 1
        if is_preference_match(b_pref, b_self):
            score += 1; matched.append(f"B {field}")
        total += 1

    # 연락 텀·머리 길이·데이트 주기
    for f in ["연락 텀", "머리 길이", "데이트 선호 주기"]:
        ra, rb = f + "(레이디)", f + "(상대방)"
        if is_preference_match(b.get(rb, "상관없음"), a.get(ra, "상관없음")):
            score += 1; matched.append(f"A {f}")
        total += 1
        if is_preference_match(a.get(rb, "상관없음"), b.get(ra, "상관없음")):
            score += 1; matched.append(f"B {f}")
        total += 1

    # 성격
    if is_preference_match(b.get("성격(상대방)"), a.get("성격(레이디)")):
        score += 1; matched.append("A 성격")
    total += 1
    if is_preference_match(a.get("성격(상대방)"), b.get("성격(레이디)")):
        score += 1; matched.append("B 성격")
    total += 1

    # 앙큼 레벨
    if list_overlap(str(a.get("양금 레벨", "")).split(","), str(b.get("희망 양금 레벨", "")).split(",")):
        score += 1; matched.append("앙금 레벨")
    total += 1

    return score, total, matched

# ===================== APP 실행 ==========================
if user_input:
    try:
        raw_df = pd.read_csv(StringIO(user_input), sep="\t")
        df = clean_df(raw_df)

        st.success("✅ 데이터 분석 성공!")
        with st.expander("🔍 입력 데이터 보기"):
            st.dataframe(df)

        results, seen = [], set()
        for i, j in permutations(df.index, 2):
            a, b = df.loc[i], df.loc[j]
            pair = tuple(sorted([a.get("닉네임"), b.get("닉네임")]))
            if pair in seen:
                continue
            seen.add(pair)
            if not (satisfies_must(a, b) and satisfies_must(b, a)):
                continue
            s, t, cond = match_score(a, b)
            pct = round(s / t * 100, 1)
            results.append({
                "A 닉네임": pair[0], "B 닉네임": pair[1],
                "매칭 점수": s, "총 점수": t,
                "비율(%)": pct, "요약": f"{s}/{t} ({pct}%)",
                "일치 조건들": ", ".join(cond)
            })

        res_df = pd.DataFrame(results).sort_values("매칭 점수", ascending=False)
        st.subheader("💘 매칭 결과")
        if res_df.empty:
            st.warning("😢 매칭 조건을 만족하는 결과가 없습니다.")
        else:
            st.dataframe(res_df)

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
