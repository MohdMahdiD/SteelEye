import datetime
import unittest
from SteelEye import ClassSteelEyeAssignment
from LoggingModule import GenericLogging

HOME_DIR = 'C:\Users\OneDrive\Desktop\SteelEye\'
LOG_DIR = "{}/log/".format(HOME_DIR)


class MyTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        """This is a setup class method  which runs as initial method
        which setup's env needed for test to run"""
        log_file = "{}/SteelEyeTest_{}.log".format(LOG_DIR, datetime.date.today().strftime('%Y%m%d'))
        cls.logger = GenericLogging(logfile=log_file)
        cls.assignment = ClassSteelEyeAssignment(logger=cls.logger)
        cls.logger.logMsg("Test Started @ {}".format(datetime.datetime.now()))

    @classmethod
    def tearDownClass(cls) -> None:
        """This is class method which runs at the end after completion of test """
        cls.logger.logMsg("Test Ended @ {}".format(datetime.datetime.now()))

    def clear_old_files_test(self):
        """This is a test method to test clear/delete old files
        Input : None
        Output : Boolean True -> Test Passed , False -> Test Failed
        """
        rtn = True

        try:
            self.assignment.clear_old_files()
        except Exception as e:
            self.logger.logError('clear_old_files_test Failed {}'.format(str(e)))
            rtn = False

        return rtn

    def get_files_for_download_test(self):
        """This is a test method to test to parase main xml and get the file names to be downloaded
        Input : None
        Output : Boolean True -> Test Passed , False -> Test Failed
        """
        rtn = True
        files_to_download = None
        try:
            files_to_download = self.assignment.get_files_to_download()
        except Exception as e:
            self.logger.logError('get_files_for_download_test Failed {}'.format(str(e)))
            rtn = False
        return rtn, files_to_download

    def download_unzip_files_test(self, files_to_download):
        """This is a test method to test if files are successfully download and zip files are unzipped
        Input : None
        Output : Boolean True -> Test Passed , False -> Test Failed
        """
        rtn = True
        try:
            self.assignment.download_and_unzip(files_to_download)
        except Exception as e:
            rtn = False
            self.logger.logError('download_unzip_files_test Failed {}'.format(str(e)))

        return rtn

    def read_and_process_xml_test(self):
        """This is a test method to test if unzipped xml zip are processed and pandas dataframe are created by combining all xml files
        Input : None
        Output : Boolean True -> Test Passed , False -> Test Failed
        """
        rtn = True
        try:
            df = self.assignment.read_and_process_xml()
        except Exception as e:
            rtn = False
            self.logger.logError('read_and_process_xml_test Failed {}'.format(str(e)))

        return rtn, df

    def create_csv_test(self, df):
        """This is a test method to test if csv file is created out of pandas dataframe
        Input : None
        Output : Boolean True -> Test Passed , False -> Test Failed
        """
        rtn = True
        try:
            self.assignment.create_csv(df)
        except Exception as e:
            rtn = False
            self.logger.logError('create_csv_test Failed {}'.format(str(e)))

        return rtn

    # TO DO AWS S3 bucket storage & AWS Lambda. Need AWS account credentials from SteelEye 
    # def upload_file_to_s3_test(self):
    #     """This is a test method to test uploading created csv to S3 aws
    #     Input : None
    #     Output : Boolean True -> Test Passed , False -> Test Failed
    #     """
    #     rtn = True
    #     try:
    #         self.assignment.copy_to_s3()
    #     except Exception as e:
    #         rtn = False
    #         self.logger.logError("upload_file_to_s3_test Failed {}".format(str(e)))

    #     return rtn

    def test_assignment(self):
        """This is a main diver test method , monolithic method which is executed
        Input : None
        Output : Boolean True -> Test Passed , False -> Test Failed
        """
        clear_old_files_sts = self.clear_old_files_test()
        self.assertTrue(clear_old_files_sts)
        get_files_download_sts, files_to_download = self.get_files_for_download_test()
        self.logger.logMsg("Files to DownLoad = {}".format(','.join(files_to_download)))
        self.assertTrue(get_files_download_sts)
        download_unzip_sts = self.download_unzip_files_test(files_to_download=files_to_download)
        self.assertTrue(download_unzip_sts)
        read_and_process_xml_sts, data_frame = self.read_and_process_xml_test()
        self.logger.logMsg("DataFrame  = {}".format(data_frame))
        self.assertTrue(read_and_process_xml_sts)
        create_csv_sts = self.create_csv_test(df=data_frame)
        self.assertTrue(create_csv_sts)
        # upload_file_sts = self.upload_file_to_s3_test()
        # self.assertTrue(upload_file_sts)

        # self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()