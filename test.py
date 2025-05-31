import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations
import csv

# ---------- UI ----------
st.set_page_config(page_title="💘 레이디 매칭 분석기", layout="wide")
st.markdown("""
# 💘 레이디 이어주기 매칭 분석기
복사한 TSV 데이터를 붙여넣고 **[🔍 매칭 분석 시작하기]** 버튼을 눌러주세요!
""")

user_input = st.text_area("📥 TSV 데이터 붙여넣기", height=300)
run = st.button("🔍 매칭 분석 시작하기")

# ---------- 유틸 ----------
def deduplicate_columns(cols):
    seen, new = {}, []
    for c in cols:
        if c not in seen:
            seen[c] = 1
            new.append(c)
        else:
            new.append(f"{c}.{seen[c]}"); seen[c] += 1
    return new

PATTERNS = [
    ("닉네임", "닉네임"), ("레이디 나이", "나이"), ("선호하는 상대방 레이디 나이", "선호 나이"),
    ("레이디 키를", "키"), ("상대방 레이디 키", "선호 키"), ("거주 지역", "지역"),
    ("거리 조건", "거리 조건"), ("성격(레이디)", "성격"), ("성격(상대방", "선호 성격"),
    ("머리 길이(레이디)", "머리 길이"), ("머리 길이(상대방", "선호 머리 길이"),
    ("흡연(레이디)", "흡연"), ("흡연(상대방", "선호 흡연"),
    ("음주(레이디)", "음주"), ("음주(상대방", "선호 음주"),
    ("타투(레이디)", "타투"), ("타투(상대방", "선호 타투"),
    ("벽장(레이디)", "벽장"), ("벽장(상대방", "선호 벽장"),
    ("데이트 선호 주기", "데이트 주기"), ("꼭 맞아야", "꼭 조건들")
]

def clean_columns(df):
    df.columns = deduplicate_columns(df.columns)
    df.columns = (df.columns.str.strip(' "')
                           .str.replace("\n", " ")
                           .str.replace("  +", " ", regex=True))
    for patt, std in PATTERNS:
        hits = [c for c in df.columns if patt in c]
        if hits:
            df = df.rename(columns={hits[0]: std})
    return df

def parse_range(txt):
    if pd.isna(txt): return None, None
    txt = str(txt).replace('이하', '~1000').replace('이상', '0~').replace(' ', '')
    if '~' in txt:
        s, e = txt.split('~'); return float(s or 0), float(e or 1000)
    try: v = float(txt); return v, v
    except: return None, None

def in_range(val, rng):
    try: val = float(val); s, e = parse_range(rng); return s is not None and s <= val <= e
    except: return False
def in_range_list(val, rngs): return any(in_range(val, r.strip()) for r in str(rngs).split(',') if r.strip())
def pref_match(pref, target):
    prefs = [p.strip() for p in str(pref).split(',') if p.strip() and p.strip() != '상관없음']
    return any(p in str(target) for p in prefs)

MANDATORY = {
    "거리": lambda a,b: not ('단거리' in str(a['거리 조건']) and a['지역'] != b['지역']),
    "성격": lambda a,b: pref_match(a['선호 성격'], b['성격']),
    "머리 길이": lambda a,b: pref_match(a['선호 머리 길이'], b['머리 길이']),
    "키": lambda a,b: in_range(b.get('키',0), a.get('선호 키','')),
}
def must_ok(a,b):
    musts=[m.strip() for m in str(a.get('꼭 조건들','')).split(',') if m.strip()]
    return all(MANDATORY[m](a,b) if m in MANDATORY else True for m in musts)

RULES=[
    ("나이", lambda a,b: in_range_list(a['나이'], b['선호 나이']) or in_range_list(b['나이'], a['선호 나이'])),
    ("키", lambda a,b: in_range(a['키'], b['선호 키']) or in_range(b['키'], a['선호 키'])),
    ("거리", lambda a,b: a['지역']==b['지역'] or '단거리' not in str(a['거리 조건'])+str(b['거리 조건'])),
    ("성격", lambda a,b: pref_match(a['선호 성격'], b['성격']) or pref_match(b['선호 성격'], a['성격'])),
    ("머리 길이", lambda a,b: pref_match(a['선호 머리 길이'], b['머리 길이']) or pref_match(b['선호 머리 길이'], a['머리 길이'])),
    ("흡연", lambda a,b: a['흡연']==b['선호 흡연'] or b['흡연']==a['선호 흡연']),
    ("음주", lambda a,b: a['음주']==b['선호 음주'] or b['음주']==a['선호 음주']),
    ("타투", lambda a,b: a['타투']==b['선호 타투'] or b['타투']==a['선호 타투']),
    ("벽장", lambda a,b: a['벽장']==b['선호 벽장'] or b['벽장']==a['선호 벽장']),
    ("데이트 주기", lambda a,b: True)
]

def calc_score(a,b):
    pts=0; matched=[]
    for label,fn in RULES:
        if fn(a,b): pts+=1; matched.append(label)
    return pts, len(RULES), matched

# ---------- 실행 ----------
if run and user_input:
    try:
        raw = pd.read_csv(StringIO(user_input), sep='\t',
                          engine='python', quoting=csv.QUOTE_NONE,
                          dtype=str, on_bad_lines='skip')
        df = clean_columns(raw)
        if '닉네임' not in df.columns:
            st.error("❌ '닉네임' 컬럼을 찾을 수 없어요. 헤더 줄을 확인해주세요!")
            st.stop()
        df = df[df['닉네임'].str.strip()!=""].reset_index(drop=True)

        st.success("✅ 데이터 정제 완료!")
        with st.expander("정제된 데이터"):
            st.dataframe(df)

        rows=[]
        for i,j in permutations(df.index,2):
            A,B=df.loc[i],df.loc[j]
            if not (must_ok(A,B) and must_ok(B,A)): continue
            s,total,why=calc_score(A,B)
            rows.append({'A':A['닉네임'],'B':B['닉네임'],
                         '점수':f'{s}/{total}','퍼센트(%)':round(s/total*100,1),
                         '일치 조건':', '.join(why)})
        res = pd.DataFrame(rows)
        if res.empty:
            st.warning("😢 조건을 만족하는 매칭이 없습니다.")
        else:
            res = res.sort_values("퍼센트(%)", ascending=False)
            st.subheader("💘 매칭 결과")
            st.dataframe(res, use_container_width=True)


    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
