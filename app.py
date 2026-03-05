import numpy as np
from scipy.stats import t
from statistics import stdev
from scipy import stats
def two_sample(a,b,alternative):
 
    xbar1 = np.mean(a)
    xbar2 = np.mean(b)
   
    sd1 = stdev(a)
    sd2 = stdev(b)
   
    n1 = len(a)
    n2 = len(b)
   
    alpha = 0.05/2
    df = n1+n2-2
    se = np.sqrt((sd1**2)/(n1)+((sd2**2)/n2))
   
    t_table_pos = print(t.ppf(1-alpha,df))
    t_table_neg = print(t.ppf(alpha,df))
   
    tcal = ((xbar1-xbar2)-0)/se
    print(tcal)
 
    if alternative == "two-sided":
        print(2*(1-t.cdf(tcal, df)))
    elif alternative == "left":
        print((t.cdf(tcal, df)))
    elif alternative == "right":
        print(1-t.cdf(tcal, df))
    print()
   
    print(stats.ttest_ind(a,b,0,alternative = 'two-sided',equal_var=False))
 