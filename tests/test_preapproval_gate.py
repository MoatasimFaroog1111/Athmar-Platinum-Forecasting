import json
import numpy as np,pandas as pd
from platinum.preapproval_gate import evaluate

def test_source_verification_blocks_approval(tmp_path):
    n=1300;dates=pd.bdate_range("2021-01-01",periods=n,tz="UTC")
    prices=1000*np.exp(np.cumsum(np.sin(np.arange(n)/13)/100))
    daily=tmp_path/"p.csv";pd.DataFrame({"Date":dates,"Close":prices}).to_csv(daily,index=False)
    release=tmp_path/"f.csv"
    pd.DataFrame({"period_end":dates[::40][:25],"available_at":dates[::40][:25]+pd.Timedelta(days=1),
      "value":np.arange(25),"source":"fixture","unit":"x"}).to_csv(release,index=False)
    result=evaluate(daily,{"macro":str(release)},source_verified=False)
    assert result["status"]=="FAIL"
    assert result["approval_recommendation"]=="BLOCK_APPROVAL"
