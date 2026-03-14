"""日志配置""" 
import logging 
import sys 

def setup_logger(level=logging.INFO): 
    """配置根日志记录器""" 
    logging.basicConfig( 
        level=level, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
        handlers=[ 
            logging.StreamHandler(sys.stdout), 
            logging.FileHandler('./data/app.log') 
        ] 
    )
