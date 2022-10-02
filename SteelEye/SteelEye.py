import datetime
import glob
import multiprocessing
import os
import shutil
from functools import partial
from io import BytesIO
from urllib.request import urlopen
from zipfile import ZipFile
from LoggingModule import GenericLogging
import pandas as pd
import xmltodict
from contextlib import contextmanager
import boto3

# Declare Constants
HOME_DIR = 'C:\Users\OneDrive\Desktop\SteelEye'
LOG_DIR = "{}/log/".format(HOME_DIR)


@contextmanager
def poolcontext(*args, **kwargs):
    pool = multiprocessing.Pool(*args, **kwargs)
    yield pool
    pool.terminate()


def process(file, logger):
    """This function is used to parase xml to json and create pandas dataframe as multiprocess
    Input : xml file name,logger object
    Output : Pandas Dataframe
    """
    logger.logMsg('Processing {}'.format(file))
    FIN_INSTRM_LIST = ['BizData', 'Pyld', 'Document', 'FinInstrmRptgRefDataDltaRpt', 'FinInstrm']
    ISSR = 'Issr'
    FIN_ATTRS = 'FinInstrmGnlAttrbts'
    ID = 'Id'
    CLASS_FCTN_TP = 'ClssfctnTp'
    CMM_DTY_DERIV_IND = 'CmmdtyDerivInd'
    FULL_NM = 'FullNm'
    NTLY_CCY = 'NtnlCcy'

    outJsnList = []
    try:
        with open(file) as xml_file:
            data_dict = xmltodict.parse(xml_file.read())
            for keys in FIN_INSTRM_LIST:
                data_dict = data_dict.get(keys)

            for data in data_dict:
                outJsn = {ID: '', FULL_NM: '', CLASS_FCTN_TP: '', CMM_DTY_DERIV_IND: '', NTLY_CCY: '', ISSR: ''}
                for value in data.values():
                    for key, val in value.items():
                        if key == ISSR:
                            outJsn[key] = val
                        elif key == FIN_ATTRS:
                            for attrkey, attrval in val.items():
                                if attrkey == ID:
                                    outJsn[attrkey] = attrval
                                elif attrkey == CLASS_FCTN_TP:
                                    outJsn[attrkey] = attrval
                                elif attrkey == CMM_DTY_DERIV_IND:
                                    outJsn[attrkey] = attrval
                                elif attrkey == FULL_NM:
                                    outJsn[attrkey] = attrval
                                elif attrkey == NTLY_CCY:
                                    outJsn[attrkey] = attrval
                    outJsnList.append(outJsn)

        xml_file.close()
    except Exception as e:
        logger.logError("Error {} Processing {} ".format(file, str(e)))
        # raise Exception('Error Processing {}'.format(file))

    return pd.DataFrame(outJsnList)


class ClassSteelEyeAssignment:
    """This is the main Class to drive the flow"""

    def __init__(self, logger=None, main_xml=None):
        """Init Method
        Input : Logger Object , main xml
        """
        self.home_path = HOME_DIR
        self.config = '{}{}'.format(self.home_path, 'config')
        self.temp_path = '{}{}'.format(self.home_path, 'temp')
        self.download_path = '{}{}'.format(self.home_path, 'downloads')
        self.outpath = '{}{}'.format(self.home_path, 'out')
        self.archive = '{}{}'.format(self.home_path, 'archive')
        self.logger = logger
        self.main_xml = '{}/{}'.format(self.config, 'main.xml')
        if main_xml is not None:
            self.main_xml = main_xml

        self.logger.logMsg("ClassSteelEyeAssigment Object Created")

    def clear_old_files(self):
        """This method is used to clear old Files For re-run
        Input : None
        Output : None
        """
        self.logger.logMsg("Clearing Old Files.....")
        try:
            for files in os.listdir(self.download_path):
                path = os.path.join(self.download_path, files)
                os.remove(path)
            for files in os.listdir(self.outpath):
                path = os.path.join(self.outpath, files)
                os.remove(path)
        except Exception as e:
            self.logger.logError("Error Creating Old Files {}.....".format(str(e)))
            raise Exception('Error in Clearing Old Files')

        self.logger.logMsg("Done Clearing Old Files.....")

    def get_files_to_download(self):
        """This method parses mail xml and returns  the list of links for download convert xml to json for easy parsing
        Input : None
        Output : List of xml files
        """

        self.logger.logMsg("Getting Files to Download")

        download_links = []
        try:
            with open(self.main_xml) as xml_file:
                data_dict = xmltodict.parse(xml_file.read())

            xml_file.close()

            for docs in data_dict.get('response').get('result').get('doc'):
                for doc in docs.get('str'):

                    if doc.get('@name') == 'download_link':
                        link = doc.get('#text', None)
                        if link is not None:
                            download_links.append(link)
        except Exception as e:
            self.logger.logMsg("Error Getting Files to Download {}".format(str(e)))
            raise Exception('Error in Getting Files For Download')

        self.logger.logMsg("Finished Getting Files to Download")

        return download_links

    def download_and_unzip(self, file_list):
        """This method is used to download the zip files and extract the xml files
        Input : xml file list
        Output : None
        """
        self.logger.logMsg("Starting Download and unzip files")
        rtn = True
        if not len(file_list):
            self.logger.logError('Nothing to Download Return ')
            raise Exception('Nothing to Download')
        else:
            for file in file_list:
                try:
                    self.logger.logMsg("Downloading {}".format(file))
                    with urlopen(file) as zipresp:
                        with ZipFile(BytesIO(zipresp.read())) as zfile:
                            zfile.extractall(self.download_path)
                except Exception as e:
                    self.logger.logError("Error {} Downloading/Unzipping {}".format(str(e), file))
                    rtn = False
            if not rtn:
                self.logger.logError("Error Download and unzip files")
                raise Exception('Failed to Download/Unzip one or More Files')

            self.logger.logMsg("Finished Download and unzip files")

    def read_and_process_xml(self):
        """This method reads xmls and processes file as multiprocess theread and creates a dataframe
        Input : None
        Output : pandas dataframe
        """
        file_pattern_path = "{}/*.xml".format(self.download_path)

        files = glob.glob(file_pattern_path)
        ob = list(zip([self.logger] * len(files), files))

        pool_size = int(multiprocessing.cpu_count() / 2)

        try:
            # with multiprocessing.Pool(pool_size) as p:
            #    result = p.starmap(process, product(files, repeat=self.logger))
            with poolcontext(processes=pool_size) as pool:
                result = pool.map(partial(process, logger=self.logger), files)

            empty = False

            for res in result:
                if res.empty:
                    empty = True

            if empty:
                self.logger.logError("Error Processing One or More XML Files")

            return pd.concat(result)
        except Exception as e:
            self.logger.logError("Error read and processing xml".format(str(e)))
            raise Exception('Error processing XML Files')

    def create_csv(self, data_frame):
        """This Method creates a csv out of pandas dataframe in out dir
        Input : pandas datarame
        Output : None
        """
        try:
            str_time = datetime.datetime.today().strftime('%Y%m%d')
            out_file = "{}/{}.csv".format(self.outpath, str_time)
            self.logger.logMsg("Creating CSV File {}".format(out_file))
            data_frame.to_csv(out_file, index=False)

            if not os.path.exists(out_file):
                self.logger.logError('{} File is Not Created '.format(out_file))
                raise Exception('Error In Create CSV File not Found')
            self.logger.logMsg("Successfully Created {} File".format(out_file))
        except Exception as e:
            self.logger.logError('Error {} Creating File'.format(str(e)))
            raise Exception('Error In Create CSV File {}'.format(str(e)))


    # TO DO AWS S3 bucket storage & AWS Lambda. Need AWS account credentials from SteelEye
    # def copy_to_s3(self):
    #     """This method is used to copy csv file to s3 bucket
    #     Input : None
    #     Output : None
    #     """
    #     self.logger.logMsg("Copying Files to S3")
    #     str_time = datetime.datetime.today().strftime('%Y%m%d')
    #     out_file = "{}/{}.csv".format(self.outpath, str_time)

    #     try:
    #         session = boto3.Session(profile_name='default')
    #         s3_resource = session.resource('s3')
    #         BUCKET = '..........'
    #         rem_file = '{}.csv'.format(str_time)
    #         s3_resource.meta.client.upload_file(out_file, BUCKET, rem_file)
    #     except Exception as e:
    #         self.logger.logError('Error Copying Files to S3 {}'.format(str(e)))
    #         raise Exception('Error Copying Files to S3')
    #     self.logger.logMsg("Copying Files to S3 Completed")
    #     shutil.move(out_file, self.archive)


if __name__ == '__main__':
    log_file = "{}/SteelEye_{}.log".format(LOG_DIR, datetime.date.today().strftime('%Y%m%d'))
    try:
        global_logger = GenericLogging(logfile=log_file)
        global_logger.logMsg(message="Logger is Created")
    except Exception as e:
        print("Error Creating Logger {}".format(str(e)))

    try:
        global_logger.logMsg("Started Process @ {}".format(datetime.datetime.now()))
        assignment = ClassSteelEyeAssignment(logger=global_logger)
        assignment.clear_old_files()
        download_links_list = assignment.get_files_to_download()
        assignment.download_and_unzip(download_links_list)
        df = assignment.read_and_process_xml()
        assignment.create_csv(data_frame=df)
        # assignment.copy_to_s3()
        global_logger.logMsg(" Process Completed Successfully @ {}".format(datetime.datetime.now()))
    except Exception as e:
        global_logger.logError(str(e))
        global_logger.logMsg(" Process Ended UnSuccessfully @ {}".format(datetime.datetime.now()))