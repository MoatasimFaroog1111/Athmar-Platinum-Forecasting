"use client";
import {useEffect,useMemo,useState} from "react";

type LatestForecast={created_at:string;origin_date:string;target_date:string;forecast_usd_kg:number;p10_usd_kg:number;p90_usd_kg:number;record_hash:string};
type Horizon={horizon_days:number;model:string;feature_group:string;interval_q90_abs_logreturn:number;mode:string;status:string;latest_forecast?:LatestForecast|null};
type MetalState={
  metal:{key:string;label:string;symbol:string};
  product:{name:string;mode:string;environment:string};
  market:{status:string;last_actual_date:string|null;last_price_usd_kg:number|null;instrument:string};
  approval:{protocol_id:string;status:string;origin_start:string;origin_end:string;score_not_before_utc:string;metrics_revealed:boolean;nominal_interval_coverage:number;minimum_mature_origins_per_horizon:number};
  horizons:Horizon[];
  context:{title:string;status:string;metrics:Record<string,number>;footnote:string};
  journal:{status:string;count:number;latest:Array<Record<string,unknown>>;latest_by_horizon?:Record<string,LatestForecast>};
  integrity:{prospective_holdout_metrics_exposed:boolean;journal_outcomes_scored?:boolean;locked_model_source?:string;official_fundamentals_in_v1?:boolean;cftc_used_for_approval?:boolean};
};
type Payload={default_metal:string;metal_order:string[];metals:Record<string,MetalState>};

const fmt=(v:number|null,dp=0)=>v==null?"—":new Intl.NumberFormat("en-US",{maximumFractionDigits:dp}).format(v);
const pct=(v:number)=>(v*100).toFixed(0)+"%";
const labelize=(s:string)=>s.replaceAll("_"," ").replace(/w/g,c=>c.toUpperCase());
const contextValue=(v:number)=>Math.abs(v)>=1000?fmt(v,0):Math.abs(v)<10?fmt(v,2):fmt(v,1);

function Sparkline(){
  const pts=[94,91,93,88,90,86,82,84,78,79,74,76,71,69,72,67,66,63,65,61,59,62,58,56,57,53,55,51,52,48];
  const path=pts.map((p,i)=>(i?"L ":"M ")+(i*(600/(pts.length-1)))+" "+p).join(" ");
  const fill="M 0 "+pts[0]+" "+pts.slice(1).map((p,i)=>"L "+((i+1)*(600/(pts.length-1)))+" "+p).join(" ")+" L 600 150 L 0 150 Z";
  return <svg viewBox="0 0 600 150" className="spark" aria-hidden="true">
    <defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#8fffd4" stopOpacity=".32"/><stop offset="1" stopColor="#8fffd4" stopOpacity="0"/></linearGradient></defs>
    <path d={path} fill="none" stroke="#8fffd4" strokeWidth="4" strokeLinecap="round"/>
    <path d={fill} fill="url(#fill)"/>
  </svg>
}

export default function Home(){
  const [payload,setPayload]=useState<Payload|null>(null);
  const [selected,setSelected]=useState("platinum");
  const [error,setError]=useState(false);

  useEffect(()=>{
    let live=true;
    const load=()=>fetch("/api/state",{cache:"no-store"}).then(r=>r.json()).then((x:Payload)=>{
      if(!live)return;
      setPayload(x);
      setSelected(prev=>x.metals[prev]?prev:x.default_metal);
      setError(false);
    }).catch(()=>live&&setError(true));
    load();const id=setInterval(load,60000);return()=>{live=false;clearInterval(id)};
  },[]);

  const data=payload?.metals[selected] ?? null;
  const candidate=useMemo(()=>data?.horizons.find(x=>x.mode==="candidate"),[data]);
  if(!payload||!data) return <main className="loading"><div className="orb"/><p>{error?"Unable to read platform state":"Connecting to Athmar engine…"}</p></main>;

  const priceLabel=data.market.last_price_usd_kg?"$"+fmt(data.market.last_price_usd_kg,0):"Waiting for live price";
  const contextEntries=Object.entries(data.context.metrics).slice(0,4);
  const isLocked=data.approval.status==="LOCKED";
  const journalActive=data.journal.status==="active";

  return <main className="shell">
    <aside className="sidebar">
      <div className="brandMark">A</div>
      <nav>
        <button className="navActive">⌁<span>Overview</span></button>
        <button>◫<span>Forecasts</span></button>
        <button>◌<span>Drivers</span></button>
        <button>◇<span>Model Lab</span></button>
        <button>▤<span>Journal</span></button>
        <button>✓<span>Approval</span></button>
      </nav>
      <div className="sideFooter"><span className="pulse"/><small>Shadow engine</small></div>
    </aside>

    <section className="content">
      <header className="topbar">
        <div>
          <p className="eyebrow">ATHMAR / PRECIOUS METALS</p>
          <h1>{data.metal.label} Intelligence</h1>
        </div>
        <div className="topActions">
          <label className="metalPicker">
            <span>Metal</span>
            <select value={selected} onChange={e=>setSelected(e.target.value)} aria-label="Select precious metal">
              {payload.metal_order.map(k=><option value={k} key={k}>{payload.metals[k]?.metal.label ?? labelize(k)}</option>)}
            </select>
          </label>
          <span className={"badge lock "+(!isLocked?"pending":"")}>● {data.approval.status}</span>
          <span className="badge shadow">{data.product.mode}</span>
        </div>
      </header>

      <section className="heroGrid">
        <article className="card hero">
          <div className="heroHead">
            <div>
              <span className="label">{data.metal.label.toUpperCase()} · USD/KG · {data.metal.symbol}</span>
              <div className="price">{priceLabel}</div>
              <p className="muted">{data.market.last_actual_date?"Last actual · "+data.market.last_actual_date:"Waiting for the first live Shadow snapshot"}</p>
            </div>
            <div className="statusRing"><span>V1</span><small>{isLocked?"locked":"setup"}</small></div>
          </div>
          <Sparkline/>
          <div className="heroFooter">
            <span>Instrument <strong>{data.market.instrument}</strong></span>
            <span>Holdout <strong>{data.approval.origin_start+" → "+data.approval.origin_end}</strong></span>
            <span>Coverage target <strong>{pct(data.approval.nominal_interval_coverage)}</strong></span>
          </div>
        </article>

        <article className="card approvalCard">
          <div className="cardTitle"><span>Approval Gate</span><b>{data.approval.protocol_id}</b></div>
          <div className="gateTrack">
            {["Data PIT","Nested WF","Model Lock","Shadow Journal","Final Score"].map((x,i)=>{
              const done=isLocked && (i<3 || (i===3&&journalActive));
              const active=(isLocked&&i===3&&!journalActive)||(!isLocked&&i===0);
              return <div key={x} className={"gate "+(done?"done":active?"active":"")}><span>{done?"✓":active?"●":"○"}</span><p>{x}</p></div>
            })}
          </div>
          <div className="unlock">
            <small>Scoring unlock</small>
            <strong>{new Date(data.approval.score_not_before_utc).toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric"})}</strong>
          </div>
          <p className="note">Each metal has an independent prospective lock. Platinum results are never reused to approve another metal.</p>
        </article>
      </section>

      <section className="sectionHead"><div><p className="eyebrow">LOCKED FORECAST STACK</p><h2>Horizon models</h2></div><span className="micro">refreshes every 60s</span></section>
      <section className="horizonGrid">
        {data.horizons.length?data.horizons.map(h=><article className={"card horizon "+(h.mode==="candidate"?"candidate":"")} key={h.horizon_days}>
          <div className="horizonTop"><span>{h.horizon_days+"D"}</span><em>{h.mode==="candidate"?"MODEL":"BASELINE"}</em></div>
          <h3>{h.latest_forecast?"$"+fmt(h.latest_forecast.forecast_usd_kg,0):(h.model==="no_change"?"No-change":h.model.replace("_"," α "))}</h3>
          <p>{h.latest_forecast?("Target · "+h.latest_forecast.target_date):labelize(h.feature_group)}</p>
          <div className="metricRow"><span>{h.latest_forecast?"P10 / P90":"90% interval"}</span><strong>{h.latest_forecast?("$"+fmt(h.latest_forecast.p10_usd_kg,0)+" / $"+fmt(h.latest_forecast.p90_usd_kg,0)):("±"+(Math.expm1(h.interval_q90_abs_logreturn)*100).toFixed(1)+"%")}</strong></div>
          <div className="miniBar"><i style={{width:Math.min(100,12+h.horizon_days*.72)+"%"}}/></div>
        </article>):<article className="card emptyWide"><strong>V1 bootstrap in progress</strong><p>Nested Walk-Forward is selecting this metal's locked candidates before any forecasts are shown.</p></article>}
      </section>

      <section className="lowerGrid">
        <article className="card fundamentals">
          <div className="cardTitle"><span>{data.context.title}</span><b>{labelize(data.context.status)}</b></div>
          <div className="fundGrid">
            {contextEntries.length?contextEntries.map(([k,v])=><div key={k}><small>{labelize(k)}</small><strong>{contextValue(v)}{selected==="platinum"?" koz":""}</strong></div>):
              <div className="contextEmpty"><small>Status</small><strong>Awaiting first feed</strong></div>}
          </div>
          <div className="fundFoot">{data.context.footnote}</div>
        </article>

        <article className="card journal">
          <div className="cardTitle"><span>Forecast Journal</span><b>{data.journal.count+" records"}</b></div>
          <div className="journalEmpty">
            <div className="seal">⌁</div>
            <h3>{journalActive?"Shadow journal active":"Ready for first live forecast"}</h3>
            <p>Every forecast is timestamped before the target outcome and tied to this metal's independent locked model.</p>
          </div>
        </article>

        <article className="card integrity">
          <div className="cardTitle"><span>Integrity</span><b>Fail-closed</b></div>
          <ul>
            <li><span>Prospective metrics exposed</span><strong>{data.integrity.prospective_holdout_metrics_exposed?"YES":"NO"}</strong></li>
            <li><span>Journal outcomes scored</span><strong>{data.integrity.journal_outcomes_scored?"YES":"NO"}</strong></li>
            <li><span>Learned candidate</span><strong>{candidate?candidate.model:"—"}</strong></li>
            <li><span>Official fundamentals V1</span><strong>{data.integrity.official_fundamentals_in_v1===false?"NO":selected==="platinum"?"WPIC":"—"}</strong></li>
            <li><span>Protocol</span><strong>{data.approval.protocol_id.replace("ATHMAR_","")}</strong></li>
          </ul>
        </article>
      </section>
      <footer>ATHMAR PRECIOUS METALS INTELLIGENCE · FOUR INDEPENDENT SHADOW SYSTEMS · NO AUTOMATED TRADING</footer>
    </section>
  </main>;
}
