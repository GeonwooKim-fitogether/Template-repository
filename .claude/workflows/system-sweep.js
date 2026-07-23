export const meta = {
  name: 'system-sweep',
  description: '시스템층 수평 스윕 — 파트(change·home·quality·specification·projects…)를 가로지르는 5개 수평 축을 시스템 레벨에서 감사한다. 파트 팀은 각자 자기 파트만 보므로 축을 가로지르는 균열(척추 위반·스키마↔문서 드리프트·디자인 이탈·파트 흐름 단절·STATUS 자기모순)을 놓친다. 이 스윕은 기존 kimlead-verified 엔진을 그대로 재사용해 렌즈별 팬아웃 → 발견마다 적대 검증 → 완결성 비평을 돌려, 사람에게는 확정된 균열과 갈림길만 올린다.',
  whenToUse: '분기 정기 감사(doc-governance.md §3), 또는 여러 파트의 PR이 쌓인 뒤 수평 축의 정합이 깨졌는지 시스템 레벨에서 확인하고 싶을 때. args로 repo·refuters·maxFindingsPerLens·lensKeys·enginePath를 조정할 수 있다. 토큰을 크게 쓰므로(에이전트 수십 개) 판돈이 클 때만 돌린다.',
  phases: [
    { title: '팬아웃', detail: '수평 렌즈별 독립 검토자가 균열을 수집한다 (kimlead-verified가 수행)' },
    { title: '적대 검증', detail: '발견마다 회의론자들이 반박을 시도하고, 다수가 반박하면 폐기한다' },
    { title: '완결성 비평', detail: '수평 축 중 통째로 안 본 각도가 없는지 점검한다' },
  ],
}

// ── 입력 (모두 선택) ──────────────────────────────────────────────────────
// args.repo               감사할 저장소 루트 경로. 기본은 이 HTS 클론 경로.
// args.enginePath         재사용할 kimlead-verified 엔진의 절대경로. 기본은 이 저장소 것.
// args.refuters           발견 하나당 붙는 회의론자 수. 기본 3 (다수결 폐기).
// args.maxFindingsPerLens 렌즈당 최대 발견 수. 기본 4.
// args.lensKeys           돌릴 렌즈 키 배열(부분 감사용). 기본은 5개 전부.
//                         키: 'spine' | 'schema-doc' | 'design' | 'cross-flow' | 'status'
const input = (typeof args === 'string' && args) ? JSON.parse(args) : (args || {})
const REPO = input.repo || '/home/user/Hardware-Team-System'
const ENGINE = input.enginePath || '/home/user/Hardware-Team-System/.claude/workflows/kimlead-verified.js'
const refuters = input.refuters || 3
const maxFindingsPerLens = input.maxFindingsPerLens || 4

// 5개 수평 렌즈. 각 렌즈 문자열은 "무엇을 보는가 + 어디를 여는가"를 자족적으로 담는다.
// kimlead-verified는 렌즈 하나당 독립 검토자 1명을 붙이고, 검토자는 여기 적힌
// 파일을 Read로 직접 열어(필요하면 Grep/Glob/Bash로 탐색) 확인한다.
const LENS = {
  spine:
    '척추(Spine) 규칙 준수 — 이 시스템의 핵심 불변식은 "부품의 Rev·Phase는 오직 Change(ECO)가 ' +
    'Effective 상태가 될 때만 바뀐다. 직접 변경은 금지"이다. 이 불변식이 코드에서 깨지는 곳을 찾아라. ' +
    '다음을 확인한다: (a) 서버 액션 app/src/lib/actions/** 에서 item_revision 의 rev 나 phase(lifecycle) 를 ' +
    'Change 발효 경로(DB 함수 make_change_effective 계열) 밖에서 직접 UPDATE/INSERT 하는 코드, ' +
    '(b) 마이그레이션 supabase/migrations/** 에서 rev/phase 를 바꾸는 트리거·RPC 가 발효 이외 경로로 열려 있는지, ' +
    '(c) RLS 가 Released 리비전의 rev제어(rev-controlled) 속성 직접 변경을 실제로 막는지. ' +
    '척추를 우회하는 쓰기 경로가 있으면 파일·함수·줄과 함께 보고하라. 우회가 없다고 판단하면 빈 배열.',
  'schema-doc':
    '스키마 ↔ 문서 드리프트 — doc-governance.md 규칙 2는 "코드(=supabase/migrations/**)가 스키마의 진실이고, ' +
    'docs/1-data-model/README.md(개념 모델)·docs/2-build/sitemap-erd.html(ERD 시각)·docs/2-build/supabase-schema.md(설명본) 는 ' +
    '이를 설명·투영하므로 마이그레이션 추가 시 함께 갱신"을 요구한다. 최근 마이그레이션(예: 0033 change_schematic_source, ' +
    '0034 quality_catalog[qa_product], 0038 spec_attr_template, 0039 quality_soft_delete / spec_product_image, ' +
    '0040 change_evidence, 0041 team_roster 등)이 개념 모델 README 에 실제로 반영됐는지 대조하라. ' +
    '또한 마이그레이션 파일 번호가 중복(같은 NNNN 을 둘 이상 파일이 공유: 0034·0036·0038·0039·0040 계열)돼 ' +
    '적용 순서 모호성을 만드는지 확인하라. 문서에 빠졌거나 어긋난 테이블·컬럼을 구체적으로 보고.',
  design:
    '디자인 정합 — 디자인 정본은 docs/design-tokens.md(Ground Control GC 토큰 → antd ConfigProvider)와 ' +
    'prototypes/prototype-app.html(화면 수용 기준)이다. 각 파트 화면이 이 정본에서 이탈한 곳을 찾아라. ' +
    'app/src/app/globals.css 와 app/src/theme/**, 파트별 View 컴포넌트 app/src/components/** 에서 ' +
    '(a) 토큰(--teal/--ink/--border/--signal 등)을 우회한 하드코딩 색·간격, ' +
    '(b) CSS 변수 폴백값이 실제 토큰값과 다른 경우(예: var(--teal, #xxxxxx) 의 폴백이 design-tokens.md 의 --teal 과 불일치), ' +
    '(c) 파트끼리 같은 요소(카드·상태 pill·표)를 서로 다르게 그리는 불일치를 확인해 파일·선택자와 함께 보고.',
  'cross-flow':
    '파트 간 흐름 단절 — 한 파트의 산출이 다른 파트로 이어지는 수평 흐름이 코드에서 끊긴 곳을 찾아라. ' +
    '확인할 사슬 예: (a) Change(ECO) 가 Effective 가 되면 그 결과가 Home 워크리스트/대시보드에 뜨고 Item 의 Rev 를 바꾸는 사슬, ' +
    '(b) Quality 시험 제·개정이 ECO(척추)를 재사용하는 사슬, (c) Specification 근거(change_evidence)가 Change 와 연결되는 사슬. ' +
    'app/src/lib/data/** 와 app/src/lib/actions/** 에서 파트 경계를 넘는 참조(예: dashboard 가 change·project·project_task 를 읽는 경로)가 ' +
    '실제로 양쪽 다 연결돼 있는지, 한쪽만 구현되고 반대쪽이 비어 흐름이 죽었는지 확인해 보고.',
  status:
    'STATUS 자기모순 — STATUS.md 의 서술끼리, 또는 STATUS 와 실제 코드가 모순되는 곳을 찾아라. ' +
    '예: §0 에서 어떤 항목을 완료(✅)로 적었으나 대응하는 코드·마이그레이션·e2e 가 없거나 그 반대인 경우, ' +
    '"pre-v3 = 코어 밖" 류의 낡은 서술이 v3 구현과 충돌하는 경우, "(0027)" 처럼 참조한 마이그레이션 번호가 이미 다른 파일에 쓰인 경우, ' +
    '"라이브 미적용" 표기와 supabase/APPLY_PENDING.sql 내용의 불일치. ' +
    'STATUS 의 특정 줄을 실제 파일과 대조해 모순을 구체적으로 보고. 실제 코드를 열어 확인한 것만 적는다.',
}

const allKeys = ['spine', 'schema-doc', 'design', 'cross-flow', 'status']
const keys = (input.lensKeys && input.lensKeys.length) ? input.lensKeys.filter(k => LENS[k]) : allKeys
const lenses = keys.map(k => LENS[k])

log(`시스템 수평 스윕 — 대상 저장소: ${REPO}`)
log(`렌즈 ${lenses.length}개(${keys.join(', ')}) · 발견당 회의론자 ${refuters}명 · 렌즈당 상한 ${maxFindingsPerLens}건`)
log(`엔진: kimlead-verified 재사용 (${ENGINE})`)

// 기존 검증 엔진을 그대로 재사용한다(중복 구현 금지). 이름 해석에 견디도록 절대경로로 건다.
// 한 단계 중첩만 허용되므로 이 워크플로가 부모, kimlead-verified 가 자식이다.
const result = await workflow({ scriptPath: ENGINE }, {
  goal:
    '이 저장소가 파트(change·home·quality·specification·projects…)를 가로지르는 5개 수평 축 — ' +
    '척추 규칙, 스키마↔문서 정합, 디자인 정합, 파트 간 흐름, STATUS 정합 — 을 지키는지, ' +
    '파트 팀 혼자서는 볼 수 없는 시스템 레벨의 균열을 찾아 확정한다.',
  target:
    `${REPO} (저장소 루트). 각 렌즈에 적힌 파일을 Read 로 직접 열고, 필요하면 Grep/Glob/Bash 로 탐색해 확인한다.`,
  lenses,
  refuters,
  maxFindingsPerLens,
})

// kimlead-verified 의 반환(goal·target·lensesUsed·confirmed·dropped·missingAngles)을 그대로 올린다.
// 침묵의 상한 금지: 폐기된 발견과 안 본 각도도 결과에 남아 온다.
return { sweep: 'system-horizontal', repo: REPO, lensKeys: keys, ...result }
