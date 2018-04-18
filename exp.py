import os
import sys
import zipfile

import networkx as nx
import pandas as pd
from time import gmtime, strftime
import logging

import setup
import session
import expctl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    input_file = sys.argv[1]
    filename, file_ext = os.path.splitext(os.path.basename(input_file))
    strtime = str(strftime('%d-%b_%H:%M', gmtime()))

    zip_name = filename + strtime + '.zip'
    zip_file = zipfile.ZipFile(zip_name, 'w')

    # Set up parameters for the session
    params = expctl.get_params(input_file)

    # Initialise dataframes to contain trading and daily data
    ddat_df = pd.DataFrame()
    tdat_df = pd.DataFrame()

    # Initialise network
    logger.info('Creating network')
    (n_traders, buy_network, sell_network) = setup.build_network(params['traders_spec'], params['network_type'])
    nx.write_adjlist(buy_network, 'network.txt')
    zip_file.write('network.txt')
    os.remove('network.txt')

    # Run sequence of trials, 1 session per trial
    trial = 1
    logger.info('Running NLSE experiments')
    while trial < params['n_trials'] + 1:
        trial_id = 'trial%04d' % trial
        logger.info('Running %s' % trial_id)
        # Initialise traders
        traders = {}
        init_verbose = False
        setup.populate_market(params['traders_spec'], traders, buy_network, sell_network, init_verbose)
        ddat, tdat = session.run(trial_id, params['start'],
                                 params['end'], params['order_sched'],
                                 traders, n_traders,
                                 buy_network, sell_network)
        # Add trading and day data from trial to df
        ddat_df = ddat_df.append(ddat)
        tdat_df = tdat_df.append(tdat)
        trial += 1

    logger.info('Experiments finished')

    # Write dataframes to csv and to zipfile
    logger.info('Writing day data to csv...')
    zip_file.writestr(filename + '_ddat.csv', ddat_df.to_csv(index=False))
    logger.info('Writing trading data to csv...')
    zip_file.writestr(filename + '_tdat.csv', tdat_df.to_csv(index=False))

    zip_file.close()
    sys.exit('Complete')

