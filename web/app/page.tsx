"use client";
import {useEffect,useMemo,useState} from "react";

type LatestForecast={created_at:string;origin_date:string;target_date:string;forecast_usd_kg:number;p10_usd_kg:number;p90_usd_kg:number;record_hash:string};\ntype Horizon={horizon_days:number;model:string;feature_group:string;interval_q90_abs_logreturn:number;mode:string;status:string;latest_forecast?:LatestForecast|null};
type State={
 product:{name:string;mode:string;environment:string};
 market:{status:string;last_actual_date:string|null;last_price_usd_kg:number|null;instrument:string};
 approval:{protocol_id:string;status:string;origin_start:string;origin_end:string;score_not_before_utc:string;metrics_revealed:boolean;nominal_interval_coverage:number;minimum_mature_origins_per_horizon:number};
 horizons:Horizon[];
 fundamentals:{wpic:{status:string;vintage?:string|null;published_at?:string|null;year?:number;unit?:string;metrics:Record<string,number>}};
 journal:{status:string;count:number;latest:Array<Record<string,unknown>>};
 integrity:{prospective_holdout_metrics_exposed:boolean;cftc_used_for_approval:boolean;locked_model_source:string};
};

const fmt=(v:number|null,dp=0)=>v==null?"—":new Intl.NumberFormat("en-US",{maximumFractionDigits:dp}).format(v);
const pct=(v:number)=>(v*100).toFixed(0)+"%";

function Sparkline(){
  const pts=[94,91,93,88,90,86,82,84,78,79,74,76,71,69,72,67,66,63,65,61,59,62,58,56,57,53,55,51,52,48];
  const path=pts.map((p,i)=>(i?"L ":"M ")+(i*(600/(pts.length-1)))+" "+p).join(" ");
  const fill="M 0 "+pts[0]+" "+pts.slice(1).map((p,i)=>"L "+((i+1)*(600/(pts.length-1)))+" "+p).join(" ")+" L 600 150 L 0 150 Z";
  return <svg viewBox="0 0 600 150" className="spark" role="img" aria-label="Decorative market trend">
    <defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#8fffd4" stopOpacity=".32"/><stop offset="1" stopColor="#8fffd4" stopOpacity="0"/></linearGradient></defs>
    <path d={path} fill="none" stroke="#8fffd4" strokeWidth="4" strokeLinecap="round"/>
    <path d={fill} fill="url(#fill)"/>
  </svg>
}

export default function Home(){
  const [data,setData]=useState<State|null>(null);
  const [error,setError]=useState(false);
  useEffect(()=>{
    let live=true;
    const load=()=>fetch("/api/state",{cache:"no-store"}).then(r=>r.json()).then(x=>{if(live){setData(x);setError(false)}}).catch(()=>live&&setError(true));
    load();const id=setInterval(load,60000);return()=>{live=false;clearInterval(id)};
  },[]);
  const candidate=useMemo(()=>data?.horizons.find(x=>x.mode==="candidate"),[data]);
  if(!data) return <main className="loading"><div className="orb"/><p>{error?"Unable to read platform state":"Connecting to Athmar engine…"}</p></main>;

  const wpic=data.fundamentals.wpic;
  const balance=wpic.metrics?.["Balance"];
  const demand=wpic.metrics?.["Total Demand"];
  const supply=wpic.metrics?.["Total Supply"];
  const priceLabel=data.market.last_price_usd_kg?"$"+fmt(data.market.last_price_usd_kg,0):"Waiting for live price";

  return <main className="shell">
    <aside className="sidebar">
      <div className="brandMark">A</div>
      <nav>
        <button className="navActive">⌁<span>Overview</span></button>
        <button>◫<span>Forecasts</span></button>
        <button>◌<span>Fundamentals</span></button>
        <button>◇<span>Model Lab</span></button>
        <button>▤<span>Journal</span></button>
        <button>✓<span>Approval</span></button>
      </nav>
      <div className="sideFooter"><span className="pulse"/><small>Shadow engine</small></div>
    </aside>

    <section className="content">
      <header className="topbar">
        <div><p className="eyebrow">ATHMAR / PRECIOUS METALS</p><h1>Platinum Intelligence</h1></div>
        <div className="topActions">
          <span className="badge lock">● {data.approval.status}</span>
          <span className="badge shadow">{data.product.mode}</span>
          <button className="iconBtn">⋯</button>
        </div>
      </header>

      <section className="heroGrid">
        <article className="card hero">
          <div className="heroHead">
            <div><span className="label">PLATINUM · USD/KG</span><div className="price">{priceLabel}</div>
            <p className="muted">{data.market.last_actual_date?"Last actual · "+data.market.last_actual_date:"Connect Shadow output to populate live market data"}</p></div>
            <div className="statusRing"><span>V1</span><small>locked</small></div>
          </div>
          <Sparkline/>
          <div className="heroFooter">
            <span>Instrument <strong>{data.market.instrument}</strong></span>
            <span>Holdout <strong>{data.approval.origin_start+" → "+data.approval.origin_end}</strong></span>
            <span>Coverage target <strong>{pct(data.approval.nominal_interval_coverage)}</strong></span>
          </div>
        </article>

        <article className="card approvalCard">
          <div className="cardTitle"><span>Approval Gate</span><b>Prospective V1</b></div>
          <div className="gateTrack">
            {["Data PIT","Nested WF","Model Lock","Shadow Journal","Final Score"].map((x,i)=><div key={x} className={i<3?"gate done":i===3?"gate active":"gate"}><span>{i<3?"✓":i===3?"●":"○"}</span><p>{x}</p></div>)}
          </div>
          <div className="unlock">
            <small>Scoring unlock</small>
            <strong>{new Date(data.approval.score_not_before_utc).toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric"})}</strong>
          </div>
          <p className="note">Prospective metrics remain sealed. Any model change requires a new future holdout.</p>
        </article>
      </section>

      <section className="sectionHead"><div><p className="eyebrow">LOCKED FORECAST STACK</p><h2>Horizon models</h2></div><span className="micro">refreshes every 60s</span></section>
      <section className="horizonGrid">
        {data.horizons.map(h=><article className={"card horizon "+(h.mode==="candidate"?"candidate":"")} key={h.horizon_days}>
          <div className="horizonTop"><span>{h.horizon_days+"D"}</span><em>{h.mode==="candidate"?"MODEL":"BASELINE"}</em></div>
          <h3>{h.latest_forecast?"$"+fmt(h.latest_forecast.forecast_usd_kg,0):(h.model==="no_change"?"No-change":h.model.replace("_"," α "))}</h3>
          <p>{h.latest_forecast?("Target · "+h.latest_forecast.target_date):(h.feature_group==="price_only"?"Price-only locked baseline":"Market + WPIC levels + engineered vintages")}</p>
          <div className="metricRow"><span>{h.latest_forecast?"P10 / P90":"90% interval"}</span><strong>{h.latest_forecast?("$"+fmt(h.latest_forecast.p10_usd_kg,0)+" / $"+fmt(h.latest_forecast.p90_usd_kg,0)):("±"+(Math.expm1(h.interval_q90_abs_logreturn)*100).toFixed(1)+"%")}</strong></div>
          <div className="miniBar"><i style={{width:Math.min(100,12+h.horizon_days*.72)+"%"}}/></div>
        </article>)}
      </section>

      <section className="lowerGrid">
        <article className="card fundamentals">
          <div className="cardTitle"><span>WPIC Fundamentals</span><b>{wpic.status==="available"?wpic.vintage:"Awaiting feed"}</b></div>
          <div className="fundGrid">
            <div><small>Total supply</small><strong>{supply!=null?fmt(supply)+" koz":"—"}</strong></div>
            <div><small>Total demand</small><strong>{demand!=null?fmt(demand)+" koz":"—"}</strong></div>
            <div><small>Balance</small><strong className={balance!=null&&balance<0?"negative":""}>{balance!=null?fmt(balance)+" koz":"—"}</strong></div>
            <div><small>Vintage date</small><strong>{wpic.published_at?new Date(wpic.published_at).toLocaleDateString("en-GB"):"—"}</strong></div>
          </div>
          <div className="fundFoot">Exact-date vintages · next-UTC-day availability · no reconstructed values</div>
        </article>

        <article className="card journal">
          <div className="cardTitle"><span>Forecast Journal</span><b>{data.journal.count+" records"}</b></div>
          <div className="journalEmpty">
            <div className="seal">⌁</div>
            <h3>{data.journal.status==="active"?"Shadow journal active":"Ready for first live forecast"}</h3>
            <p>Every live prediction is timestamped before the target outcome and tied to the locked model hash.</p>
          </div>
        </article>

        <article className="card integrity">
          <div className="cardTitle"><span>Integrity</span><b>Fail-closed</b></div>
          <ul>
            <li><span>Prospective metrics exposed</span><strong>{data.integrity.prospective_holdout_metrics_exposed?"YES":"NO"}</strong></li>
            <li><span>CFTC in approval lock</span><strong>{data.integrity.cftc_used_for_approval?"YES":"NO"}</strong></li>
            <li><span>90D candidate</span><strong>{candidate?candidate.model:"—"}</strong></li>
            <li><span>Journal outcomes scored</span><strong>{data.integrity.journal_outcomes_scored?"YES":"NO"}</strong></li>\n            <li><span>Source</span><strong>model_lock_v1</strong></li>
          </ul>
        </article>
      </section>
      <footer>ATHMAR PLATINUM INTELLIGENCE · RESEARCH SHADOW MODE · NO AUTOMATED TRADING</footer>
    </section>
  </main>;
}
