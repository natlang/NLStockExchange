import os
import sys
import zipfile
import pandas as pd
import time
from time import gmtime, strftime
import logging

import setup
import session
import expctl
import data

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.WARNING,
    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    start = time.time()

    input_file = sys.argv[1]
    filename, file_ext = os.path.splitext(os.path.basename(input_file))
    # strtime = str(strftime('%d-%b_%H:%M', gmtime()))

    zip_name = filename + '.zip'
    zip_file = zipfile.ZipFile(zip_name, 'w')

    # Set up parameters for the session
    params = expctl.get_params(input_file)

    # Initialise dataframes to contain trading and daily data
    ddat_df = pd.DataFrame()
    tdat_df = pd.DataFrame()

    # Initialise network
    logger.info('Creating network')
    (n_traders, buy_network, sell_network) = setup.build_network(params['traders_spec'], params['network'])
    data.write_adj_matrix(zip_file, buy_network)
    ndat = data.init_ndat(params['traders_spec'], params['n_days'])

    # Run sequence of trials, 1 session per trial
    trial = 1
    logger.info('Running NLSE experiments')
    while trial < params['n_trials'] + 1:
        logger.info('Running %s' % trial)
        # Initialise traders
        traders = {}
        init_verbose = False
        setup.populate_market(params['traders_spec'], traders, buy_network, sell_network, init_verbose)
        ddat, tdat = session.run(trial, params['start'],
                                 params['end'], params['order_sched'],
                                 traders, n_traders,
                                 ndat, buy_network, sell_network)
        # Add trading and day data from trial to df
        ddat_df = ddat_df.append(ddat)
        tdat_df = tdat_df.append(tdat)
        ndat_df = data.get_ndat_df(ndat, buy_network)
        trial += 1

    logger.info('Experiments finished')

    # Write dataframes to csv and to zipfile
    logger.info('Writing day data to csv...')
    zip_file.writestr(filename + '_ddat.csv', ddat_df.to_csv(index=False))
    logger.info('Writing trading data to csv...')
    zip_file.writestr(filename + '_tdat.csv', tdat_df.to_csv(index=False))
    logger.info('Writing network data to csv...')
    zip_file.writestr(filename + '_ndat.csv', ndat_df.to_csv(index=False))
    # Draw network graphs and write to zipfile
    logger.info('Drawing network graphs...')
    data.draw_network(ndat, params['n_days'], buy_network, sell_network, zip_file)

    zip_file.close()

    end = time.time()
    print(end - start)
    sys.exit('Complete')

