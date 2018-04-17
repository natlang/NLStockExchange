import os
import sys
import time
import zipfile
import pandas as pd

import session
import expctl

if __name__ == '__main__':
    # start = time.time()
    input_file = sys.argv[1]
    filename, file_ext = os.path.splitext(os.path.basename(input_file))

    # Set up parameters for the session
    params = expctl.get_params(input_file)

    # Initialise dataframes to contain trading and daily data
    ddat_df = pd.DataFrame()
    tdat_df = pd.DataFrame()

    # Run sequence of trials, 1 session per trial
    # n_trials = 1
    trial = 1
    while trial < params['n_trials'] + 1:
        trial_id = 'trial%04d' % trial
        ddat, tdat = session.run(trial_id, params['start'], params['end'], params['traders_spec'], params['network_type'], params['order_sched'])
        # Add trading and day data from trial to df
        ddat_df = ddat_df.append(ddat)
        tdat_df = tdat_df.append(tdat)
        trial += 1

    # Write dataframes to csv and to zipfile
    with zipfile.ZipFile(filename + '.zip', 'w') as z:
        z.writestr(filename + '_ddat.csv', ddat_df.to_csv(index=False))
        z.writestr(filename + '_tdat.csv', tdat_df.to_csv(index=False))
        z.close()

    # print("--- %s seconds ---" % (time.time() - start))
    sys.exit('Complete')

