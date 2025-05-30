# lady_matching_app.py  – 2025-05-31 안정판
# ──────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

# ===================== UI ===============================
st.set_page_config(page_title="레이디 매칭 분석기", layout="wide")
st.title("💘 레이디 이어주기 매칭 분석기 2.0")
st.markdown("#### 📋 구글 폼 TSV 응답을 그대로 붙여넣어주세요")
user_input = st.text_area("📥 응답 데이터를 붙여넣으세요", height=300)

# ===================== 정제 함수 =========================
def clean_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.dropna(axis=1, how="all")
    df = df.loc[:, ~df.columns.duplicated()]
    df.columns = df.columns.str.strip().str.replace(r"\s+", " ", regex=True)

    # ── 긴 질문 → 표준 열 이름 ───────────────────────────
    rename_map = {"데이트 선호 주기": "데이트 선호 주기(레이디)"}
    kw = {
        "닉네임": "닉네임",
        "레이디 나이": "레이디 나이",
        "선호하는 상대방 레이디 나이": "선호하는 상대방 레이디 나이",
        "레이디 키": "레이디 키",
        "상대방 레이디 키": "상대방 레이디 키",
        "레이디의 거주 지역": "레이디의 거주 지역",
        "희망하는 거리 조건": "희망하는 거리 조건",
    }
    for std, key in kw.items():
        if std not in df.columns:
            hit = [c for c in df.columns if key in c]
            if hit:
                rename_map[hit[0]] = std
    df = df.rename(columns=rename_map)

    # ── 숫자형 변환 ─────────────────────────────────────
    for c in ["레이디 키", "레이디 나이"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # ── (레이디)/(상대방) 조건 필드가 없으면 기본값 채우기 ──
    bases = ["흡연", "음주", "타투", "벽장", "퀴어 지인 多",
             "연락 텀", "머리 길이", "데이트 선호 주기"]
    for base in bases:
        for suf in ["(레이디)", "(상대방)"]:
            col = f"{base}{suf}"
            if col not in df.columns:
                df[col] = "상관없음"

    # (상대방) 나머지 필드
    other_missing = [
        "데이트 선호 주기(상대방)", "연락 텀(상대방)", "머리 길이(상대방)",
        "흡연(상대방)", "음주(상대방)", "타투(상대방)", "벽장(상대방)",
        "퀴어 지인 多(상대방)"
    ]
    for c in other_missing:
        if c not in df.columns:
            df[c] = "상관없음"

    # ── 불필요 열 제거 ──────────────────────────────────
    drop_cols = [
        "응답 시간", "손톱길이(농담)", "연애 텀", "",
        "더 추가하고 싶으신 이상언니(형)과 레이디 소개 간단하게 적어주세요!!"
    ]
    return df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

# ===================== 범위·일치 함수 ====================
def parse_range(txt):
    try:
        if pd.isna(txt): return (None, None)
        txt = str(txt).strip()
        if not txt or txt == "~": return (None, None)
        if "~" in txt:
            low, high = txt.replace(" ", "").split("~")
            return (float(low), float(high) if high else None)
        return (float(txt), float(txt))
    except:
        return (None, None)

def is_in_range(val, rng):
    try:
        val = float(val)
    except:
        return False
    low, high = parse_range(rng)
    return low is not None and high is not None and low <= val <= high

def is_in_range_list(val, rngs):
    return any(is_in_range(val, r.strip()) for r in str(rngs).split(",") if r.strip())

def list_overlap(a, b):
    bs = {y.strip() for y in b}
    return any(x.strip() in bs for x in a if x.strip())

def pref_match(pref, target):
    if pd.isna(pref) or pd.isna(target): return False
    prefs = [x.strip() for x in str(pref).split(",")]
    return "상관없음" in prefs or str(target).strip() in prefs

# ===================== 필수 조건 ==========================
def must_ok(a, b):
    for c in map(str.strip, str(a.get("꼭 맞아야 조건들", "")).split(",")):
        if c == "거리" and a.get("희망하는 거리 조건") == "단거리":
            if a.get("레이디의 거주 지역") != b.get("레이디의 거주 지역"):
                return False
        elif c == "성격" and not pref_match(a.get("성격(상대방)"), b.get("성격(레이디)")):
            return False
        elif c == "머리 길이" and not pref_match(a.get("머리 길이(상대방)"), b.get("머리 길이(레이디)")):
            return False
        elif c == "앙큼 레벨" and not list_overlap(
            str(a.get("희망 양금 레벨", "")).split(","),
            str(b.get("양금 레벨", "")).split(",")):
            return False
    return True

# ===================== 점수 계산 ==========================
def score_pair(a, b):
    s, t, m = 0, 0, []

    # 나이·키
    if is_in_range_list(a["레이디 나이"], b["선호하는 상대방 레이디 나이"]):
        s += 2; m.append("A 나이→B")
    t += 1
    if is_in_range_list(b["레이디 나이"], a["선호하는 상대방 레이디 나이"]):
        s += 2; m.append("B 나이→A")
    t += 1
    if is_in_range(a["레이디 키"], b["상대방 레이디 키"]):
        s += 1; m.append("A 키→B")
    t += 1
    if is_in_range(b["레이디 키"], a["상대방 레이디 키"]):
        s += 1; m.append("B 키→A")
    t += 1

    # 거리
    if a["희망하는 거리 조건"] == "단거리" or b["희망하는 거리 조건"] == "단거리":
        if a["레이디의 거주 지역"] == b["레이디의 거주 지역"]:
            s += 1; m.append("거리 일치(단)")
        t += 1
    else:
        s += 1; m.append("거리 무관"); t += 1

    # 흡연·음주… 
    for base in ["흡연", "음주", "타투", "벽장", "퀴어 지인 多"]:
        if pref_match(b[f"{base}(상대방)"], a[f"{base}(레이디)"]):
            s += 1; m.append("A " + base)
        t += 1
        if pref_match(a[f"{base}(상대방)"], b[f"{base}(레이디)"]):
            s += 1; m.append("B " + base)
        t += 1

    # 연락 텀·머리 길이·데이트 주기
    for base in ["연락 텀", "머리 길이", "데이트 선호 주기"]:
        if pref_match(b[f"{base}(상대방)"], a[f"{base}(레이디)"]):
            s += 1; m.append("A " + base)
        t += 1
        if pref_match(a[f"{base}(상대방)"], b[f"{base}(레이디)"]):
            s += 1; m.append("B " + base)
        t += 1

    # 성격
    if pref_match(b["성격(상대방)"], a["성격(레이디)"]):
        s += 1; m.append("A 성격")
    t += 1
    if pref_match(a["성격(상대방)"], b["성격(레이디)"]):
        s += 1; m.append("B 성격")
    t += 1

    # 앙큼 레벨
    if list_overlap(str(a["양금 레벨"]).split(","), str(b["희망 양금 레벨"]).split(",")):
        s += 1; m.append("앙큼 레벨")
    t += 1

    return s, t, m

# ===================== APP 실행 ==========================
if user_input:
    try:
        raw_df = pd.read_csv(StringIO(user_input), sep="\t")
        df = clean_df(raw_df)

        st.success("✅ 데이터 정제 완료")
        with st.expander("📄 정제 데이터 보기"):
            st.dataframe(df)

        results, seen = [], set()
        for i, j in permutations(df.index, 2):
            a, b = df.loc[i], df.loc[j]
            pair = tuple(sorted([a["닉네임"], b["닉네임"]]))
            if pair in seen: continue
            seen.add(pair)
            if not (must_ok(a, b) and must_ok(b, a)): continue
            sc, tot, cond = score_pair(a, b)
            pct = round(sc / tot * 100, 1)
            results.append({
                "A 닉네임": pair[0], "B 닉네임": pair[1],
                "매칭 점수": sc, "총 점수": tot,
                "일치율(%)": pct, "조건 일치": ", ".join(cond)
            })

        res_df = pd.DataFrame(results).sort_values("매칭 점수", ascending=False)
        st.subheader("💘 매칭 결과")
        if res_df.empty:
            st.warning("😢 매칭 조건을 만족하는 결과가 없습니다.")
        else:
            st.dataframe(res_df)

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
