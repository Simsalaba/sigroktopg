#!/usr/bin/env python3

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from subprocess import PIPE, Popen
import psycopg2

deviceId = 0
testSessionId = 0

ampFactor = {"mA": 1e-3, "A": 1, "uA": 1e-6}

voltFactor = {"mV": 1e-3, "V": 1, "uV": 1e-6}


def main():
    args = parseArguments()

    try:
        print("Connecting to {}".format(args.host))
        connection = psycopg2.connect(
            user=args.dbUser,
            password=args.password,
            host=args.host,
            port=args.port,
            database=args.db,
        )
        cursor = connection.cursor()
        start_time = datetime.utcnow()
        start_time_timestamp = datetime.utcnow().isoformat()

        pgq_create_new_device = """ INSERT INTO device (devicename, devicephysicalid) VALUES (%s,%s) ON CONFLICT (devicephysicalid) DO UPDATE SET devicename = (%s) RETURNING id; """
        data = (args.deviceName, args.deviceId, args.deviceName)
        cursor.execute(
            pgq_create_new_device,
            (data),
        )

        pgq_get_device_id = """ SELECT id FROM device WHERE devicename = (%s); """

        pgq_create_new_test_session = """ INSERT INTO testsession (datetimestarted, testsessionname, commitid, username, notes) VALUES (%s,%s,%s,%s,%s); """
        pgq_get_test_session_id = (
            """ SELECT id FROM testsession WHERE testsessionname = (%s); """
        )

        cursor.execute(pgq_get_device_id, (args.deviceName,))
        deviceId = cursor.fetchone()[0]

        data = (
            start_time_timestamp,
            str(args.testSessionName),
            str(args.commitId),
            str(args.user),
            args.notes,
        )
        cursor.execute(pgq_create_new_test_session, (data))
        cursor.execute(pgq_get_test_session_id, (args.testSessionName,))
        testSessionId = cursor.fetchone()[0]
        connection.commit()
        data_stream = Popen(
            [
                "sigrok-cli",
                "--driver",
                "{}:conn={}".format(args.driver, args.usbPort),
                "--continuous",
            ],
            stdout=PIPE,
        )

        time_limit_reached = False
        while time_limit_reached != True:
            print("Running test...")
            for line in data_stream.stdout:
                input = line.decode("utf-8").strip().split(" ")
                if args.verbose:
                    print(input)
                tDelta = datetime.now() - start_time
                seconds = round((tDelta.total_seconds() - 3600), 2)
                timestamp = datetime.utcnow().isoformat()
                unit = input[2][-1]

                pgq_create_new_data_point = """ INSERT INTO datapoint (value, deviceid, testsessionid, seconds, timestamp, unit) VALUES (%s,%s,%s,%s,%s,%s); """
                data_to_insert = (
                    float(input[1]) * ampFactor[input[2]],
                    int(deviceId),
                    int(testSessionId),
                    seconds,
                    timestamp,
                    unit,
                )

                cursor.execute(pgq_create_new_data_point, (data_to_insert))
                time = timedelta(
                    seconds=tDelta.seconds, milliseconds=tDelta.microseconds / 1000
                ).total_seconds()
                connection.commit()
                if seconds >= float(args.testTime):
                    time_limit_reached = True
                    data_stream.terminate()
                    print("Ran test for {}".format(seconds)+"s")

        if connection:
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL", error)
        sys.exit("Exiting!")


def parseArguments():

    commandlineparser = argparse.ArgumentParser(
        description="Sends Sigrok-cli data to the powerprofilerDB"
    )

    commandlineparser.add_argument(
        "--commitId",
        default="N/A",
        help="Git commit ID of the FW. Defaults to '%(default)s'",
    )
    commandlineparser.add_argument(
        "--dbUser", default="", help="Database user name"
    )
    commandlineparser.add_argument(
        "--db",
        default="",
        help="Database name. Defaults to '%(default)s'",
    )
    commandlineparser.add_argument(
        "--deviceId", default="", help="The board's UUID")
    commandlineparser.add_argument(
        "--deviceName", default="", help="deviceName")
    commandlineparser.add_argument(
        "--driver",
        default="uni-t-ut61c-ser",
        help="sigrok driver. Defaults to '%(default)s'",
    )
    commandlineparser.add_argument(
        "--host",
        default="localhost",
        help="PostgresDB host name. Defaults to '%(default)s'",
    )
    commandlineparser.add_argument(
        "--notes",
        default="N/A",
        help="Optional information about the test. Defaults to '%(default)s'",
    )
    commandlineparser.add_argument(
        "--password", default="", help="DB user password."
    )
    commandlineparser.add_argument(
        "--port", default=5432, help="DB port number. Defaults to '%(default)s'"
    )
    commandlineparser.add_argument(
        "--testSessionName", default="", help="Test session name"
    )
    commandlineparser.add_argument(
        "--testTime", default=0, help="Test time in seconds"
    )
    commandlineparser.add_argument(
        "--user", default="", help="Name of the person running the test"
    )
    commandlineparser.add_argument(
        "--usbPort",
        default="/dev/ttyUSB0",
        help="USB port of the multimeter. Defaults to '%(default)s'",
    )
    commandlineparser.add_argument("-v", "--verbose", action="store_true",
                                   help="verbose output")

    db = "powerprofilingdb"

    args = commandlineparser.parse_args()

    if args.deviceName == "":
        sys.exit("deviceName argument must be provided")

    if args.user == "":
        sys.exit("user argument must be provided")

    if args.deviceId == "":
        sys.exit("deviceId argument must be provided")

    if args.testSessionName == "":
        sys.exit("testSessionName argument must be provided")

    return args


if __name__ == "__main__":
    main()
