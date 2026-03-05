from flask import Flask,request,jsonify
import numpy as np
from scipy.stats import t
from statistics import stdev
from scipy import stats

app = Flask(__name__)

@app.route("/ttest",methods=["POST"])
def ttest():

    data=request.json

    a=data["sampleA"]
    b=data["sampleB"]
    alternative=data["alternative"]

    xbar1=np.mean(a)
    xbar2=np.mean(b)

    sd1=stdev(a)
    sd2=stdev(b)

    n1=len(a)
    n2=len(b)

    df=n1+n2-2

    se=np.sqrt((sd1**2)/n1 + (sd2**2)/n2)

    tcal=((xbar1-xbar2)-0)/se

    if alternative=="two-sided":
        p=2*(1-t.cdf(abs(tcal),df))
    elif alternative=="left":
        p=t.cdf(tcal,df)
    else:
        p=1-t.cdf(tcal,df)

    return jsonify({
        "t_value":float(tcal),
        "p_value":float(p)
    })

if __name__=="__main__":
    app.run()