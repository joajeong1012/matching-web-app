import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

# ---------- Streamlit UI ----------
st.set_page_config(page_title="레이디 매칭 분석기", layout="wide")
st.title("💘 레이디 이어주기 매칭 분석기 (v3.1)")
st.markdown("#### 📋 구글 폼 TSV 응답을 복사해서 붙여넣어 주세요")
user_input = st.text_area("📥 TSV 데이터 붙여넣기", height=300)

# ---------- 전처리 ----------
def tidy_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = (
        df.columns.str.strip().str.replace("\n", " ")
        .str.replace("  +", " ", regex=True)
    )
    # 닉네임 열 자동 매핑
    nick_cols = [c for c in df.columns if "닉네임" in c]
    if nick_cols:
        df = df.rename(columns={nick_cols[0]: "닉네임"})

    rename = {
        "레이디 나이": "나이",
        "선호하는 상대방 레이디 나이": "선호 나이",
        "레이디 키를 적어주she레즈 (숫자만 적어주세여자)": "키",
        "상대방 레이디 키를 적어주she레즈 (예시 : 154~, ~170)": "선호 키",
        "레이디의 거주 지역": "지역",
        "희망하는 거리 조건": "거리 조건",
        "성격 [성격(레이디)]": "성격",
        "성격 [성격(상대방 레이디)]": "선호 성격",
        "[머리 길이(레이디)]": "머리 길이",
        "[머리 길이(상대방 레이디)]": "선호 머리 길이",
        "[흡연(레이디)]": "흡연",
        "[흡연(상대방 레이디)]": "선호 흡연",
        "[음주(레이디)]": "음주",
        "[음주(상대방 레이디) ]": "선호 음주",
        "[타투(레이디)]": "타투",
        "[타투(상대방 레이디)]": "선호 타투",
        "[벽장(레이디)]": "벽장",
        "[벽장(상대방 레이디)]": "선호 벽장",
        "[데이트 선호 주기]": "데이트 주기",
        "꼭 맞아야 하는 조건들은 무엇인가레?": "꼭 조건들",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    df = df.fillna("")
    df["키"] = pd.to_numeric(df.get("키"), errors="coerce")
    return df

# ---------- 범위 판단 ----------
def parse_range(txt):
    if pd.isna(txt): return None, None
    txt = str(txt).replace("이하", "~1000").replace("이상", "0~").replace(" ", "")
    if "~" in txt:
        s, e = txt.split("~")
        return float(s or 0), float(e or 1000)
    try:
        v = float(txt)
        return v, v
    except:
        return None, None

def in_range(val, rng):
    try:
        val = float(val)
        mn, mx = parse_range(rng)
        return mn is not None and mn <= val <= mx
    except:
        return False

def in_range_list(val, rngs):
    return any(in_range(val, r.strip()) for r in str(rngs).split(",") if r.strip())

# ---------- 점수 계산 ----------
PREF_FIELDS = [
    ("흡연", "선호 흡연"), ("음주", "선호 음주"), ("타투", "선호 타투"),
    ("벽장", "선호 벽장"), ("머리 길이", "선호 머리 길이"),
]

EXTRA_FIELDS = ["데이트 주기"]  # 상관없음/허용 체크용

POINTS = {
    "나이": 2,
    "키": 2,
    "거리": 1,
    "성격": 1,
    "기타 선호": 1,
}

def preference_ok(pref_value, target_value):
    if not pref_value: return True
    pref_list = [x.strip() for x in str(pref_value).split(",")]
    return "상관없음" in pref_list or str(target_value).strip() in pref_list


def calc_score(a, b):
    score = 0
    total = 0

    # 나이
    total += POINTS["나이"]
    if in_range_list(a["나이"], b["선호 나이"]) and in_range_list(b["나이"], a["선호 나이"]):
        score += POINTS["나이"]

    # 키
    total += POINTS["키"]
    if in_range(a["키"], b["선호 키"]) and in_range(b["키"], a["선호 키"]):
        score += POINTS["키"]

    # 거리(지역)
    total += POINTS["거리"]
    if ("단거리" not in a["거리 조건"] and "단거리" not in b["거리 조건"]) or (a["지역"] == b["지역"]):
        score += POINTS["거리"]

    # 성격
    total += POINTS["성격"]
    if preference_ok(a["선호 성격"], b["성격"]) and preference_ok(b["선호 성격"], a["성격"]):
        score += POINTS["성격"]

    # 흡연/음주/타투/벽장/머리 길이 등 기타 선호
    for self_col, pref_col in PREF_FIELDS:
        total += POINTS["기타 선호"]
        if preference_ok(a[pref_col], b[self_col]) and preference_ok(b[pref_col], a[self_col]):
            score += POINTS["기타 선호"]

    # 데이트 주기 (가벼운 보너스)
    for fld in EXTRA_FIELDS:
        if fld in a and fld in b and a[fld] and b[fld]:
            total += 1
            if preference_ok(a[fld], b[fld]) and preference_ok(b[fld], a[fld]):
                score += 1

    return score, total

# ---------- 필수 조건 ----------
def must_satisfied(a, b):
    musts = [m.strip() for m in str(a.get("꼭 조건들", "")).split(",") if m.strip()]
    for m in musts:
        if m == "거리" and "단거리" in a["거리 조건"] and a["지역"] != b["지역"]:
            return False
        if m == "성격" and not preference_ok(a["선호 성격"], b["성격"]):
            return False
        if m == "머리 길이" and not preference_ok(a["선호 머리 길이"], b["머리 길이"]):
            return False
        if m == "키" and not in_range(b["키"], a["선호 키"]):
            return False
        if m == "흡연" and not preference_ok(a["선호 흡연"], b["흡연"]):
            return False
        if m == "음주" and not preference_ok(a["선호 음주"], b["음주"]):
            return False
    return True

# ---------- 실행 ----------
if user_input:
    try:
        raw = pd.read_csv(StringIO(user_input), sep="\t")
        df = tidy_cols(raw).dropna(subset=["닉네임"]).reset_index(drop=True)

        st.success("✅ 데이터 정제 완료!")
        with st.expander("📄 정제된 데이터"):
            st.dataframe(df)

        rows = []
        seen = set()
        for i, j in permutations(df.index, 2):
            if i >= j: continue
            A, B = df.loc[i], df.loc[j]
            key = tuple(sorted([A["닉네임"], B["닉네임"]]))
            if key in seen: continue
            if not (must_satisfied(A, B) and must_satisfied(B, A)):
                continue
            s, t = calc_score(A, B)
            rows.append({"A": A["닉네임"], "B": B["닉네임"], "점수": f"{s}/{t}", "퍼센트(%)": round(s/t*100, 1)})
            seen.add(key)

        res = pd.DataFrame(rows).sort_values("퍼센트(%)", ascending=False)
        if res.empty:
            st.warning("😢 조건을 만족하는 매칭이 없습니다.")
        else:
            st.subheader("💘 매칭 결과")
            st.dataframe(res.reset_index(drop=True))

    except Exception as err:
        st.error(f"❌ 분석 실패: {err}")

