import mysql.connector


def create_connection_master():
    mydb = mysql.connector.connect(
        host="119.252.175.26",
        user="admin",
        password="S!MGos2@kemkes.go.id",
        database="master"
    )
    return mydb


def create_connection_pegawai():
    mydb = mysql.connector.connect(
        host="119.252.175.26",
        user="admin",
        password="S!MGos2@kemkes.go.id",
        database="pegawai"
    )
    return mydb


def close_connection(mydb):
    mydb.close()
