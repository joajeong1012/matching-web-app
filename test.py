import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

# ===================== Streamlit UI =====================
st.set_page_config(page_title="💘 레이디 매칭 분석기", layout="wide")
st.markdown("""
# 💘 레이디 이어주기 매칭 분석기

서로의 조건을 바탕으로 궁합을 분석해줍니다 💖

TSV 데이터를 붙여넣고 **[🔍 매칭 분석 시작하기]** 버튼을 눌러주세요!
""")

user_input = st.text_area("📥 TSV 데이터 붙여넣기", height=300)
run = st.button("🔍 매칭 분석 시작하기")

# ===================== 전처리 함수 =====================

def deduplicate_columns(cols: pd.Index) -> pd.Index:
    seen = {}
    new_cols = []
    for c in cols:
        if c not in seen:
            seen[c] = 1
            new_cols.append(c)
        else:
            seen[c] += 1
            new_cols.append(f"{c}.{seen[c]-1}")
    return pd.Index(new_cols)

# 핵심 컬럼을 부분문자열로 매핑
PATTERN_MAP = [
    ("닉네임", "닉네임"),
    ("레이디 나이", "나이"),
    ("선호하는 상대방 레이디 나이", "선호 나이"),
    ("레이디 키를", "키"),
    ("상대방 레이디 키", "선호 키"),
    ("레이디의 거주 지역", "지역"),
    ("희망하는 거리 조건", "거리 조건"),
    ("성격(레이디)", "성격"),
    ("성격(상대방 레이디)", "선호 성격"),
    ("머리 길이(레이디)", "머리 길이"),
    ("머리 길이(상대방 레이디)", "선호 머리 길이"),
    ("흡연(레이디)", "흡연"),
    ("흡연(상대방 레이디)", "선호 흡연"),
    ("음주(레이디)", "음주"),
    ("음주(상대방 레이디)", "선호 음주"),
    ("타투(레이디)", "타투"),
    ("타투(상대방 레이디)", "선호 타투"),
    ("벽장(레이디)", "벽장"),
    ("벽장(상대방 레이디)", "선호 벽장"),
    ("데이트 선호 주기", "데이트 주기"),
    ("꼭 맞아야 하는 조건", "꼭 조건들"),
]

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    # 1) 중복 이름 해결
    df.columns = deduplicate_columns(df.columns)
    # 2) 양 끝 공백+따옴표 제거, 줄바꿈 -> 공백
    df.columns = (df.columns
                  .str.strip(' "')
                  .str.replace("\n", " ")
                  .str.replace("  +", " ", regex=True))
    # 3) 패턴 기반 매핑
    for patt, std in PATTERN_MAP:
        for col in df.columns:
            if patt in col:
                df = df.rename(columns={col: std})
                break
    return df

# ===================== 매칭 로직 =====================

def parse_range(txt):
    if pd.isna(txt):
        return None, None
    txt = str(txt).replace('이하', '~1000').replace('이상', '0~').replace(' ', '')
    if '~' in txt:
        s, e = txt.split('~')
        return float(s or 0), float(e or 1000)
    try:
        v = float(txt)
        return v, v
    except:
        return None, None

def in_range(val, txt):
    try:
        val = float(val)
        s, e = parse_range(txt)
        return s is not None and s <= val <= e
    except:
        return False

def in_range_list(val, txts):
    return any(in_range(val, p.strip()) for p in str(txts).split(',') if p.strip())

def has_overlap(pref, target):
    prefs = [p.strip() for p in str(pref).split(',') if p.strip() and p.strip() != '상관없음']
    return any(p in str(target) for p in prefs)

MANDATORY_CHECKS = {
    "거리": lambda a, b: not ('단거리' in str(a['거리 조건']) and a['지역'] != b['지역']),
    "성격": lambda a, b: has_overlap(a['선호 성격'], b['성격']),
    "머리 길이": lambda a, b: has_overlap(a['선호 머리 길이'], b['머리 길이']),
    "키": lambda a, b: in_range(b.get('키', 0), a.get('선호 키', '')),
}

def must_ok(a, b):
    musts = [m.strip() for m in str(a.get('꼭 조건들', '')).split(',') if m.strip()]
    for m in musts:
        if m in MANDATORY_CHECKS and not MANDATORY_CHECKS[m](a, b):
            return False
    return True

SCORE_RULES = [
    ("나이", lambda a, b: in_range_list(a['나이'], b['선호 나이']) or in_range_list(b['나이'], a['선호 나이'])),
    ("키", lambda a, b: in_range(a['키'], b['선호 키']) or in_range(b['키'], a['선호 키'])),
    ("거리", lambda a, b: a['지역'] == b['지역'] or '단거리' not in str(a['거리 조건']) + str(b['거리 조건'])),
    ("성격", lambda a, b: has_overlap(a['선호 성격'], b['성격']) or has_overlap(b['선호 성격'], a['성격'])),
    ("머리 길이", lambda a, b: has_overlap(a['선호 머리 길이'], b['머리 길이']) or has_overlap(b['선호 머리 길이'], a['머리 길이'])),
    ("흡연", lambda a, b: a['흡연'] == b['선호 흡연'] or b['흡연'] == a['선호 흡연']),
    ("음주", lambda a, b: a['음주'] == b['선호 음주'] or b['음주'] == a['선호 음주']),
    ("타투", lambda a, b: a['타투'] == b['선호 타투'] or b['타투'] == a['선호 타투']),
    ("벽장", lambda a, b: a['벽장'] == b['선호 벽장'] or b['벽장'] == a['선호 벽장']),
]

def calc_score(a, b):
    score = 0
    reasons = []
    for label, func in SCORE_RULES:
        if func(a, b):
            score += 1
            reasons.append(label)
    # 데이트 주기 무조건 +1 (양쪽 모두 한 번만)
    score += 1
    reasons.append('데이트 주기')
    return score, len(SCORE_RULES) + 1, reasons

# ===================== 실행 =====================
if run and user_input:
    try:
        df = pd.read_csv(StringIO(user_input), sep='\t')
        df = clean_column_names(df)
        df = df[df['닉네임'].str.strip() != ''].reset_index(drop=True)

        st.success('✅ 데이터 정제 완료!')
        with st.expander('정제된 데이터 확인'):
            st.dataframe(df)

        rows = []
        for i, j in permutations(df.index, 2):
            a, b = df.loc[i], df.loc[j]
            if not (must_ok(a, b) and must_ok(b, a)):
                continue
            s, total, reasons = calc_score(a, b)
            rows.append({
                'A': a['닉네임'], 'B': b['닉네임'],
                '점수': f'{s}/{total}', '퍼센트(%)': round(s/total*100, 1),
                '일치 조건': ', '.join(reasons)
            })

        res = pd.DataFrame(rows).sort_values('퍼센트(%)', ascending=False)
        if res.empty:
            st.warning('😢 매칭 결과가 없습니다.')
        else:
            st.subheader('💘 매칭 결과')
            st.dataframe(res, use_container_width=True)

    except Exception as e:
        st.error(f'❌ 분석 실패: {e}')
