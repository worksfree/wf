import { useState, useEffect } from "react";

const STAGES = [
  {id:"상담진행중",          lb:"상담진행중",  me:false, act:"상담 내용 확인 및 현장클리닉 신청 안내"},
  {id:"신청완료",            lb:"신청완료",    me:false, act:"지방청 전화 상담 대기"},
  {id:"지방청전화상담",      lb:"전화상담완료",me:false, act:"전화 상담 완료 확인"},
  {id:"현장클리닉최종승인",  lb:"최종승인",    me:false, act:"기업의 위원 선정 대기"},
  {id:"클리닉위원선정",      lb:"위원선정",    me:true,  act:"수행계획서 등록"},
  {id:"수행계획서등록",      lb:"계획서작성",  me:false, act:"계획서 제출 확인"},
  {id:"수행계획서승인",      lb:"계획서승인",  me:true,  act:"기업 부담금 납부 안내"},
  {id:"기업입금확인요청",    lb:"기업입금",    me:false, act:"운영기관 확인 대기"},
  {id:"운영기관입금확인",    lb:"입금확인",    me:true,  act:"현장클리닉 수행"},
  {id:"현장클리닉수행중",    lb:"수행중",      me:true,  act:"현장지도결과서 등록"},
  {id:"현장지도결과서등록",  lb:"결과서등록",  me:false, act:"결과서 승인 대기"},
  {id:"현장지도결과서승인",  lb:"결과서승인",  me:true,  act:"전자세금계산서 등록"},
  {id:"세금계산서발행완료",  lb:"세금계산서",  me:false, act:"만족도 조사 독려"},
  {id:"만족도조사",          lb:"만족도조사",  me:false, act:"자문료 지급 대기"},
  {id:"자문료지급대기",      lb:"지급대기",    me:false, act:"자문료 입금 확인"},
  {id:"자문료지급",          lb:"완  료",      me:false, act:"완료"},
];

const SI = Object.fromEntries(STAGES.map((s,i) => [s.id, i]));
const MY = new Set(STAGES.filter(s => s.me).map(s => s.id));
const getS = id => STAGES[SI[id]] ?? STAGES[0];

const FIELDS = ["경영전략","창업","마케팅","기술","인사/노무","회계(세무)","정보화","생산관리","수출입","특허","법무","금융"];

const FEES = {
  "일반": {
    1:{contract:350000,  gov:280000,  company:70000,  vat:35000,  actual:105000, tax:385000},
    2:{contract:700000,  gov:560000,  company:140000, vat:70000,  actual:210000, tax:770000},
    3:{contract:1050000, gov:840000,  company:210000, vat:105000, actual:315000, tax:1155000},
  },
  "면제": {
    1:{contract:350000,  gov:350000,  company:0, vat:35000,  actual:35000,  tax:385000},
    2:{contract:700000,  gov:700000,  company:0, vat:70000,  actual:70000,  tax:770000},
    3:{contract:1050000, gov:1050000, company:0, vat:105000, actual:105000, tax:1155000},
  }
};

const fw  = n => (n||0).toLocaleString()+"원";
const uid = () => Date.now().toString(36)+Math.random().toString(36).slice(2,5);
const tod = () => new Date().toISOString().slice(0,10);
const BLANK = {id:"",company:"",ceo:"",tel:"",manager:"",managerTel:"",field:"경영전략",area:"일반",days:3,stage:"상담진행중",startDate:tod(),endDate:"",memo:"",appliedAt:tod()};

const C   = "#1e3a5f";
const inp = {width:"100%",padding:"9px 12px",border:"1px solid #d1d5db",borderRadius:8,fontSize:14,boxSizing:"border-box",background:"white",outline:"none",display:"block",fontFamily:"inherit"};

/* ── 공통 컴포넌트 ── */
function Card({title, children, style={}}) {
  return (
    <div style={{background:"white",borderRadius:12,padding:"14px 16px",boxShadow:"0 1px 4px rgba(0,0,0,0.08)",...style}}>
      {title && <div style={{fontWeight:700,fontSize:14,color:"#374151",marginBottom:10}}>{title}</div>}
      {children}
    </div>
  );
}

function Row({label, val, highlight}) {
  return (
    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"5px 0",borderBottom:"1px solid #f3f4f6",fontSize:13}}>
      <span style={{color:"#6b7280"}}>{label}</span>
      <span style={{fontWeight:highlight?700:500,color:highlight?"#166534":"#1f2937"}}>{val}</span>
    </div>
  );
}

function FI({label, children, hint}) {
  return (
    <div style={{marginBottom:10}}>
      <div style={{fontSize:12,color:"#6b7280",marginBottom:4}}>{label}</div>
      {children}
      {hint && <div style={{fontSize:11,color:"#9ca3af",marginTop:3}}>{hint}</div>}
    </div>
  );
}

function Badge({stageId}) {
  const s = getS(stageId);
  const isMe   = MY.has(stageId);
  const isDone = stageId === "자문료지급";
  return (
    <span style={{fontSize:12,fontWeight:600,padding:"2px 9px",borderRadius:999,whiteSpace:"nowrap",
      background:isDone?"#dcfce7":isMe?"#fee2e2":"#dbeafe",
      color:isDone?"#166534":isMe?"#b91c1c":"#1d4ed8"}}>
      {s.lb}
    </span>
  );
}

function Bar({stageId, invert}) {
  const pct    = Math.round((SI[stageId]/(STAGES.length-1))*100);
  const isDone = stageId === "자문료지급";
  const isMe   = MY.has(stageId);
  return (
    <div style={{background:invert?"rgba(255,255,255,0.25)":"#e5e7eb",borderRadius:4,height:5}}>
      <div style={{width:pct+"%",height:5,borderRadius:4,transition:"width 0.3s",
        background:invert?"white":isDone?"#16a34a":isMe?"#dc2626":"#3b82f6"}}/>
    </div>
  );
}

/* ── 목록 ── */
function ListPg({list, cls, stats, tab, setTab, q, setQ, onOpen, onAdd, onExport, onImport}) {
  return (
    <div style={{fontFamily:"system-ui,sans-serif",background:"#f1f5f9",minHeight:"100vh",paddingBottom:90}}>
      {/* 헤더 */}
      <div style={{background:C,padding:"20px 20px 0"}}>
        <div style={{color:"white",fontWeight:700,fontSize:18,marginBottom:14}}>📋 수진기업 관리</div>
        <div style={{display:"flex",gap:8,marginBottom:-1}}>
          {[{k:"all",l:"전체",v:stats.all},{k:"me",l:"내 액션",v:stats.me},{k:"done",l:"완료",v:stats.done}].map(({k,l,v}) => (
            <button key={k} onClick={()=>setTab(k)} style={{flex:1,padding:"8px 0",border:"none",borderRadius:"8px 8px 0 0",
              background:tab===k?"#f1f5f9":"rgba(255,255,255,0.15)",
              color:tab===k?C:"white",cursor:"pointer",fontWeight:600,fontFamily:"inherit"}}>
              <div style={{fontSize:20,fontWeight:700}}>{v}</div>
              <div style={{fontSize:11}}>{l}</div>
            </button>
          ))}
        </div>
      </div>
      {/* 검색 */}
      <div style={{padding:"12px 16px"}}>
        <input value={q} onChange={e=>setQ(e.target.value)} placeholder="🔍 기업명·분야·대표자 검색" style={{...inp,border:"1px solid #d1d5db"}}/>
      </div>
      {/* 카드 목록 */}
      <div style={{padding:"0 16px",display:"flex",flexDirection:"column",gap:10}}>
        {list.length === 0 && (
          <div style={{textAlign:"center",padding:"64px 0",color:"#9ca3af",fontSize:14}}>
            {cls.length === 0
              ? <span>우측 하단 <b>+</b> 버튼으로 첫 번째 수진기업을 등록하세요</span>
              : "조건에 맞는 기업이 없습니다"}
          </div>
        )}
        {list.map(c => {
          const s    = getS(c.stage);
          const f    = FEES[c.area]?.[c.days] || {};
          const isMe = MY.has(c.stage);
          const isDone = c.stage === "자문료지급";
          return (
            <div key={c.id} onClick={()=>onOpen(c.id)}
              style={{background:"white",borderRadius:12,padding:"14px 16px",
                boxShadow:"0 1px 4px rgba(0,0,0,0.08)",cursor:"pointer",
                borderLeft:`4px solid ${isDone?"#16a34a":isMe?"#dc2626":"#3b82f6"}`}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:4}}>
                <div style={{fontWeight:700,fontSize:15,color:"#111827"}}>{c.company}</div>
                <Badge stageId={c.stage}/>
              </div>
              <div style={{fontSize:12,color:"#6b7280",marginBottom:7}}>
                {c.field} · {c.days}일 · {c.area}지역{c.ceo?" · "+c.ceo:""}
              </div>
              <Bar stageId={c.stage}/>
              <div style={{display:"flex",justifyContent:"space-between",marginTop:7,fontSize:12}}>
                <span style={{color:isMe?"#b91c1c":"#6b7280",fontWeight:isMe?600:400}}>
                  {isMe?"⚡ ":""}{s.act}
                </span>
                <span style={{color:"#374151",fontWeight:500}}>{fw(f.actual)}</span>
              </div>
            </div>
          );
        })}
      </div>
      {/* FAB */}
      <button onClick={onAdd} style={{position:"fixed",bottom:24,right:20,width:54,height:54,borderRadius:"50%",background:C,color:"white",fontSize:28,border:"none",cursor:"pointer",boxShadow:"0 4px 16px rgba(0,0,0,0.25)",display:"flex",alignItems:"center",justifyContent:"center",fontFamily:"inherit"}}>+</button>
      <button onClick={onExport} style={{position:"fixed",bottom:24,right:84,height:40,borderRadius:20,background:"#059669",color:"white",fontSize:12,fontWeight:700,border:"none",cursor:"pointer",boxShadow:"0 4px 16px rgba(0,0,0,0.2)",padding:"0 14px",fontFamily:"inherit"}}>📤 백업</button>
      <button onClick={onImport} style={{position:"fixed",bottom:24,right:152,height:40,borderRadius:20,background:"#7c3aed",color:"white",fontSize:12,fontWeight:700,border:"none",cursor:"pointer",boxShadow:"0 4px 16px rgba(0,0,0,0.2)",padding:"0 14px",fontFamily:"inherit"}}>📥 복원</button>
    </div>
  );
}

/* ── 상세 ── */
function DetailPg({client:c, onEdit, onDel, onBack, onAdvance, onSetStage, aiLoad, aiTxt, onAI}) {
  const s      = getS(c.stage);
  const f      = FEES[c.area]?.[c.days] || {};
  const isMe   = MY.has(c.stage);
  const isDone = c.stage === "자문료지급";
  const idx    = SI[c.stage] ?? 0;
  const [showPicker,     setShowPicker]     = useState(false);
  const [showDelConfirm, setShowDelConfirm] = useState(false);

  return (
    <div style={{fontFamily:"system-ui,sans-serif",background:"#f1f5f9",minHeight:"100vh",paddingBottom:80}}>
      {/* 헤더 */}
      <div style={{background:C,padding:"16px 20px 20px",color:"white"}}>
        <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:14}}>
          <button onClick={onBack} style={{background:"rgba(255,255,255,0.2)",border:"none",color:"white",borderRadius:8,padding:"5px 10px",cursor:"pointer",fontSize:13,fontFamily:"inherit"}}>← 목록</button>
          <div style={{fontWeight:700,fontSize:17,flex:1,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{c.company}</div>
          <button onClick={onEdit} style={{background:"rgba(255,255,255,0.2)",border:"none",color:"white",borderRadius:8,padding:"5px 10px",cursor:"pointer",fontSize:13,fontFamily:"inherit"}}>수정</button>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:9}}>
          <Badge stageId={c.stage}/>
          <span style={{fontSize:12,opacity:0.8}}>{idx+1}/{STAGES.length} 단계</span>
        </div>
        <Bar stageId={c.stage} invert/>
      </div>

      <div style={{padding:"14px 16px",display:"flex",flexDirection:"column",gap:12}}>
        {/* 액션 배너 */}
        {!isDone && (
          <Card style={{background:isMe?"#fef2f2":"#eff6ff",border:`1px solid ${isMe?"#fca5a5":"#bfdbfe"}`,boxShadow:"none"}}>
            <div style={{fontWeight:700,color:isMe?"#b91c1c":"#1d4ed8",fontSize:13,marginBottom:4}}>
              {isMe?"⚡ 지금 해야 할 일":"⏳ 대기 중"}
            </div>
            <div style={{color:"#374151",fontSize:15,fontWeight:600,marginBottom:isMe?10:0}}>{s.act}</div>
            {isMe && idx < STAGES.length-1 && (
              <button onClick={onAdvance} style={{background:"#b91c1c",color:"white",border:"none",borderRadius:8,padding:"7px 16px",cursor:"pointer",fontSize:13,fontWeight:700,fontFamily:"inherit"}}>완료 → 다음 단계</button>
            )}
          </Card>
        )}
        {isDone && (
          <Card style={{background:"#f0fdf4",border:"1px solid #86efac",boxShadow:"none"}}>
            <div style={{textAlign:"center",color:"#166534",fontWeight:700,fontSize:15}}>✅ 현장클리닉 완료</div>
          </Card>
        )}

        {/* 진행상태 직접 변경 */}
        <div>
          <button onClick={()=>setShowPicker(v=>!v)} style={{width:"100%",background:"white",border:"1px solid #d1d5db",borderRadius:10,padding:"10px 14px",cursor:"pointer",fontSize:13,fontWeight:600,textAlign:"left",color:"#374151",fontFamily:"inherit"}}>
            {showPicker?"▲":"▼"} 진행상태 직접 변경
          </button>
          {showPicker && (
            <div style={{background:"white",border:"1px solid #e5e7eb",borderRadius:10,marginTop:4,padding:10,display:"flex",flexWrap:"wrap",gap:6}}>
              {STAGES.map(st => {
                const active = c.stage === st.id;
                return (
                  <button key={st.id} onClick={()=>{onSetStage(st.id); setShowPicker(false);}}
                    style={{padding:"5px 11px",borderRadius:999,border:"none",cursor:"pointer",fontSize:12,fontWeight:600,fontFamily:"inherit",
                      background:active?C:st.me?"#fee2e2":st.id==="자문료지급"?"#dcfce7":"#f3f4f6",
                      color:active?"white":st.me?"#b91c1c":st.id==="자문료지급"?"#166534":"#374151",
                      outline:active?"2px solid rgba(30,58,95,0.5)":"none"}}>
                    {st.lb}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* 기업 정보 */}
        <Card title="📌 기업 정보">
          {[
            ["대표자",         c.ceo||"-"],
            ["연락처",         c.tel||"-"],
            ["담당자",         c.manager||"-"],
            ["담당자 연락처",  c.managerTel||"-"],
            ["지원분야",       c.field],
            ["수행일수",       c.days+"일"],
            ["지역구분",       c.area+"지역"],
            ["수행기간",       `${c.startDate} ~ ${c.endDate||"미정"}`],
            ["신청일",         c.appliedAt],
          ].map(([k,v]) => <Row key={k} label={k} val={v}/>)}
        </Card>

        {/* 비용 정보 */}
        <Card title="💰 비용 정보">
          {[
            ["계약금액 (100%)",   fw(f.contract)],
            ["정부지원금",        fw(f.gov)],
            ["기업부담금",        fw(f.company)],
            ["VAT (10%)",         fw(f.vat)],
            ["기업 실납부액",     fw(f.actual)],
            ["세금계산서 발행액", fw(f.tax)],
          ].map(([k,v]) => <Row key={k} label={k} val={v} highlight={k==="기업 실납부액"||k==="세금계산서 발행액"}/>)}
        </Card>

        {/* 메모 */}
        {c.memo && (
          <Card title="📝 메모">
            <div style={{fontSize:13,color:"#374151",lineHeight:1.7,whiteSpace:"pre-wrap"}}>{c.memo}</div>
          </Card>
        )}

        {/* AI 추천 */}
        <Card title="🤖 AI 액션 추천">
          {!aiTxt && !aiLoad && (
            <div style={{textAlign:"center",paddingBottom:4}}>
              <p style={{fontSize:13,color:"#6b7280",marginBottom:12,lineHeight:1.6}}>현재 상태와 메모를 분석해<br/>구체적인 액션 아이템을 제안해 드립니다</p>
              <button onClick={onAI} style={{background:C,color:"white",border:"none",borderRadius:10,padding:"10px 28px",cursor:"pointer",fontSize:14,fontWeight:700,fontFamily:"inherit"}}>AI 추천 받기</button>
            </div>
          )}
          {aiLoad && (
            <div style={{textAlign:"center",padding:"20px 0",color:"#6b7280",fontSize:13}}>
              <div style={{fontSize:24,marginBottom:6}}>🔍</div>분석 중...
            </div>
          )}
          {aiTxt && (
            <div>
              <div style={{fontSize:13,color:"#1f2937",lineHeight:1.8,whiteSpace:"pre-wrap"}}>{aiTxt}</div>
              <button onClick={onAI} style={{marginTop:10,background:"#f3f4f6",color:"#374151",border:"none",borderRadius:8,padding:"7px 14px",cursor:"pointer",fontSize:12,fontFamily:"inherit"}}>↺ 다시 분석</button>
            </div>
          )}
        </Card>

        {/* 삭제 */}
        <button onClick={()=>setShowDelConfirm(true)} style={{width:"100%",background:"white",border:"1px solid #fca5a5",color:"#dc2626",borderRadius:10,padding:"11px",cursor:"pointer",fontSize:14,fontWeight:600,fontFamily:"inherit"}}>🗑 기업 삭제</button>

        {/* 삭제 확인 모달 */}
        {showDelConfirm && (
          <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.45)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:999}}>
            <div style={{background:"white",borderRadius:16,padding:"24px 20px",width:280,boxShadow:"0 8px 32px rgba(0,0,0,0.2)"}}>
              <div style={{fontWeight:700,fontSize:16,color:"#111827",marginBottom:8}}>기업 삭제</div>
              <div style={{fontSize:14,color:"#6b7280",marginBottom:20,lineHeight:1.6}}>
                <b style={{color:"#111827"}}>{c.company}</b>을(를)<br/>삭제하시겠습니까?<br/>
                <span style={{fontSize:12,color:"#ef4444"}}>삭제 후 복구할 수 없습니다.</span>
              </div>
              <div style={{display:"flex",gap:8}}>
                <button onClick={()=>setShowDelConfirm(false)} style={{flex:1,padding:"10px",border:"1px solid #d1d5db",borderRadius:8,background:"white",color:"#374151",cursor:"pointer",fontWeight:600,fontSize:14,fontFamily:"inherit"}}>취소</button>
                <button onClick={onDel} style={{flex:1,padding:"10px",border:"none",borderRadius:8,background:"#dc2626",color:"white",cursor:"pointer",fontWeight:700,fontSize:14,fontFamily:"inherit"}}>삭제</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── 등록/수정 폼 ── */
function FormPg({form, setForm, onSave, onCancel}) {
  const set = (k,v) => setForm(f => ({...f,[k]:v}));
  const fee = FEES[form.area]?.[form.days];
  return (
    <div style={{fontFamily:"system-ui,sans-serif",background:"#f1f5f9",minHeight:"100vh",paddingBottom:80}}>
      <div style={{background:C,padding:"16px 20px",display:"flex",alignItems:"center",gap:10}}>
        <button onClick={onCancel} style={{background:"rgba(255,255,255,0.2)",border:"none",color:"white",borderRadius:8,padding:"5px 10px",cursor:"pointer",fontSize:13,fontFamily:"inherit"}}>← 취소</button>
        <span style={{color:"white",fontWeight:700,fontSize:17}}>{form.company?"기업 수정":"기업 등록"}</span>
      </div>
      <div style={{padding:"16px",display:"flex",flexDirection:"column",gap:12}}>
        <Card title="📌 기업 정보">
          <FI label="기업명 *"><input value={form.company} onChange={e=>set("company",e.target.value)} style={inp} placeholder="(주)예시기업"/></FI>
          <FI label="대표자명"><input value={form.ceo} onChange={e=>set("ceo",e.target.value)} style={inp} placeholder="홍길동"/></FI>
          <FI label="연락처 (대표)"><input value={form.tel} onChange={e=>set("tel",e.target.value)} style={inp} placeholder="010-0000-0000"/></FI>
          <FI label="담당자명"><input value={form.manager||""} onChange={e=>set("manager",e.target.value)} style={inp} placeholder="담당자 이름"/></FI>
          <FI label="담당자 연락처"><input value={form.managerTel||""} onChange={e=>set("managerTel",e.target.value)} style={inp} placeholder="010-0000-0000"/></FI>
          <FI label="신청일"><input type="date" value={form.appliedAt} onChange={e=>set("appliedAt",e.target.value)} style={inp}/></FI>
        </Card>

        <Card title="📋 컨설팅 정보">
          <FI label="지원분야">
            <select value={form.field} onChange={e=>set("field",e.target.value)} style={inp}>
              {FIELDS.map(f => <option key={f}>{f}</option>)}
            </select>
          </FI>
          <FI label="지역구분">
            <div style={{display:"flex",gap:8}}>
              {["일반","면제"].map(a => (
                <button key={a} onClick={()=>set("area",a)}
                  style={{flex:1,padding:"9px",border:`2px solid ${form.area===a?C:"#d1d5db"}`,borderRadius:8,
                    background:form.area===a?C:"white",color:form.area===a?"white":"#374151",
                    cursor:"pointer",fontWeight:600,fontSize:13,fontFamily:"inherit"}}>{a}지역</button>
              ))}
            </div>
          </FI>
          <FI label="수행일수">
            <div style={{display:"flex",gap:8}}>
              {[1,2,3].map(d => (
                <button key={d} onClick={()=>set("days",d)}
                  style={{flex:1,padding:"9px",border:`2px solid ${form.days===d?C:"#d1d5db"}`,borderRadius:8,
                    background:form.days===d?C:"white",color:form.days===d?"white":"#374151",
                    cursor:"pointer",fontWeight:700,fontFamily:"inherit"}}>{d}일</button>
              ))}
            </div>
          </FI>
          {fee && (
            <div style={{background:"#f0fdf4",border:"1px solid #86efac",borderRadius:8,padding:"10px 12px",marginTop:4}}>
              <div style={{fontSize:12,fontWeight:700,color:"#166534",marginBottom:6}}>💰 비용 미리보기</div>
              {[["기업부담금",fee.company],["기업 실납부액",fee.actual],["세금계산서 발행액",fee.tax]].map(([k,v]) => (
                <div key={k} style={{display:"flex",justifyContent:"space-between",fontSize:13,padding:"2px 0"}}>
                  <span style={{color:"#6b7280"}}>{k}</span>
                  <span style={{fontWeight:700,color:"#166534"}}>{fw(v)}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="📅 일정 및 진행상태">
          <FI label="현재 진행상태">
            <select value={form.stage} onChange={e=>set("stage",e.target.value)} style={inp}>
              {STAGES.map(s => (
                <option key={s.id} value={s.id}>{s.lb}{"  "}{s.me?"⚡":""}{" "}{s.act}</option>
              ))}
            </select>
          </FI>
          <FI label="수행 시작일"><input type="date" value={form.startDate} onChange={e=>set("startDate",e.target.value)} style={inp}/></FI>
          <FI label="수행 종료일"><input type="date" value={form.endDate} onChange={e=>set("endDate",e.target.value)} style={inp}/></FI>
        </Card>

        <Card title="📝 메모">
          <textarea value={form.memo} onChange={e=>set("memo",e.target.value)} rows={4}
            placeholder="기업 특이사항, 애로사항, 담당자 요청 내용 등..."
            style={{...inp,resize:"vertical",lineHeight:1.6}}/>
        </Card>

        <button onClick={onSave} style={{width:"100%",background:C,color:"white",border:"none",borderRadius:10,padding:"14px",cursor:"pointer",fontSize:15,fontWeight:700,fontFamily:"inherit"}}>저장</button>
      </div>
    </div>
  );
}

/* ── 메인 앱 ── */
export default function App() {
  const [cls,    setCls]    = useState([]);
  const [busy,   setBusy]   = useState(true);
  const [page,   setPage]   = useState("list");
  const [selId,  setSelId]  = useState(null);
  const [form,   setForm]   = useState(null);
  const [q,      setQ]      = useState("");
  const [tab,    setTab]    = useState("all");
  const [aiLoad,     setAiLoad]     = useState(false);
  const [aiTxt,      setAiTxt]      = useState("");
  const [backupModal, setBackupModal] = useState(false);
  const [backupTxt,   setBackupTxt]   = useState("");
  const [copied,      setCopied]      = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const r = await window.storage.get("bzd_clients_v1");
        if (r) setCls(JSON.parse(r.value));
      } catch {}
      setBusy(false);
    })();
  }, []);

  const persist = async d => {
    setCls(d);
    try { await window.storage.set("bzd_clients_v1", JSON.stringify(d)); } catch {}
  };

  const sel = cls.find(c => c.id === selId);

  let list = cls;
  if (tab === "me")   list = cls.filter(c => MY.has(c.stage));
  if (tab === "done") list = cls.filter(c => c.stage === "자문료지급");
  if (q) list = list.filter(c => [c.company,c.field,c.ceo].some(v => v?.includes(q)));

  const stats = {
    all:  cls.length,
    me:   cls.filter(c => MY.has(c.stage)).length,
    done: cls.filter(c => c.stage === "자문료지급").length,
  };

  const goAdd    = ()  => { setForm({...BLANK, id:uid()}); setAiTxt(""); setPage("form"); };
  const goEdit   = c   => { setForm({...c}); setAiTxt(""); setPage("form"); };
  const goDetail = id  => { setSelId(id); setAiTxt(""); setPage("detail"); };
  const goList   = ()  => setPage("list");

  const saveForm = async () => {
    if (!form.company.trim()) { alert("기업명을 입력해 주세요."); return; }
    const exists = cls.some(c => c.id === form.id);
    await persist(exists ? cls.map(c => c.id===form.id ? form : c) : [...cls, form]);
    goList();
  };

  const delClient = async id => {
    await persist(cls.filter(c => c.id !== id));
    goList();
  };

  const advance = async c => {
    const i = SI[c.stage] ?? 0;
    if (i >= STAGES.length-1) return;
    await persist(cls.map(x => x.id===c.id ? {...x, stage:STAGES[i+1].id} : x));
  };

  const setStage = async (id, sid) => {
    await persist(cls.map(c => c.id===id ? {...c, stage:sid} : c));
  };

  const exportData = () => {
    const json = JSON.stringify(cls, null, 2);
    setBackupTxt(json);
    setCopied(false);
    setBackupModal(true);
  };

  const copyBackup = () => {
    const ta = document.getElementById("backup-textarea");
    if (!ta) return;
    ta.select();
    ta.setSelectionRange(0, 99999);
    try {
      document.execCommand("copy");
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  const importData = () => {
    const input    = document.createElement("input");
    input.type     = "file";
    input.accept   = ".json";
    input.onchange = async e => {
      const file = e.target.files[0];
      if (!file) return;
      const text = await file.text();
      try {
        const parsed = JSON.parse(text);
        if (!Array.isArray(parsed)) throw new Error();
        await persist(parsed);
        alert(`✅ ${parsed.length}개 기업 데이터가 복원되었습니다.`);
      } catch { alert("❌ 올바른 백업 파일이 아닙니다."); }
    };
    input.click();
  };

  const callAI = async c => {
    setAiLoad(true); setAiTxt("");
    const s = getS(c.stage);
    const f = FEES[c.area]?.[c.days] || {};
    try {
      const res = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 700,
          system: "당신은 중소벤처기업부 비즈니스지원단 현장클리닉 클리닉위원(경영지도사) 보조 AI입니다. 수진기업 현황을 보고, 클리닉위원이 지금 당장 취해야 할 구체적인 액션 아이템 3가지를 번호 목록으로 제안하세요. 각 항목은 1~2문장, 실무적이고 명확하게 작성하세요. 한국어로만 답하세요.",
          messages: [{role:"user", content:`[수진기업 현황]\n기업명: ${c.company}\n지원분야: ${c.field}\n현재상태: ${c.stage}\n다음액션: ${s.act}\n수행일수: ${c.days}일 / ${c.area}지역\n기업 실납부액: ${fw(f.actual)} / 세금계산서: ${fw(f.tax)}\n수행기간: ${c.startDate}~${c.endDate||"미정"}\n메모: ${c.memo||"없음"}`}]
        })
      });
      const d = await res.json();
      setAiTxt(d.content?.[0]?.text || "결과를 불러올 수 없습니다.");
    } catch {
      setAiTxt("오류가 발생했습니다. 다시 시도해 주세요.");
    }
    setAiLoad(false);
  };

  if (busy) return <div style={{display:"flex",alignItems:"center",justifyContent:"center",height:"100vh",fontFamily:"sans-serif",color:"#6b7280",fontSize:14}}>불러오는 중...</div>;
  if (page==="form"   && form) return <FormPg form={form} setForm={setForm} onSave={saveForm} onCancel={goList}/>;
  if (page==="detail" && sel)  return <DetailPg client={sel} onEdit={()=>goEdit(sel)} onDel={()=>delClient(sel.id)} onBack={goList} onAdvance={()=>advance(sel)} onSetStage={sid=>setStage(sel.id,sid)} aiLoad={aiLoad} aiTxt={aiTxt} onAI={()=>callAI(sel)}/>;
  return (
    <>
      <ListPg list={list} cls={cls} stats={stats} tab={tab} setTab={setTab} q={q} setQ={setQ} onOpen={goDetail} onAdd={goAdd} onExport={exportData} onImport={importData}/>
      {/* 백업 모달 */}
      {backupModal && (
        <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.5)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:999,padding:16}}>
          <div style={{background:"white",borderRadius:16,padding:"20px",width:"100%",maxWidth:480,boxShadow:"0 8px 32px rgba(0,0,0,0.2)"}}>
            <div style={{fontWeight:700,fontSize:16,color:"#111827",marginBottom:4}}>📤 백업 데이터</div>
            <div style={{fontSize:12,color:"#6b7280",marginBottom:10}}>아래 내용을 전체 선택 후 복사해서 메모앱·카카오톡 나에게 보내기 등에 저장하세요.</div>
            <textarea id="backup-textarea" readOnly value={backupTxt} rows={10}
              style={{...inp,fontSize:11,fontFamily:"monospace",resize:"none",background:"#f9fafb",color:"#374151"}}
              onFocus={e=>e.target.select()}/>
            <div style={{display:"flex",gap:8,marginTop:12}}>
              <button onClick={()=>setBackupModal(false)} style={{flex:1,padding:"10px",border:"1px solid #d1d5db",borderRadius:8,background:"white",color:"#374151",cursor:"pointer",fontWeight:600,fontSize:14,fontFamily:"inherit"}}>닫기</button>
              <button onClick={copyBackup} style={{flex:2,padding:"10px",border:"none",borderRadius:8,background:copied?"#059669":C,color:"white",cursor:"pointer",fontWeight:700,fontSize:14,fontFamily:"inherit"}}>
                {copied?"✅ 복사 완료!":"📋 전체 복사"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
