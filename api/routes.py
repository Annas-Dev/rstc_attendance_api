from flask import Blueprint, request, jsonify
import service
import base64
import numpy as np
import cv2
import db_connection
import uuid
from datetime import datetime
from flask_jwt_extended import create_access_token, jwt_required

blueprint = Blueprint("routes", __name__)


@blueprint.route("/")
def home():
    return "<h1>Welcome to DeepFace API!</h1>"


@blueprint.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)

    if username == 'rstc' and password == 'rstc@2023':
        # Jika otentikasi berhasil, kita buat token JWT
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify(message='Login gagal'), 401


@blueprint.route("/verify", methods=["POST"])
@jwt_required()
def verify():
    input_args = request.get_json()

    if input_args is None:
        return {"message": "isian tidak boleh kosong"}

    img1_path = input_args.get("img1_path")
    img2_path = input_args.get("img2_path")

    if img1_path is None:
        return {"message": "you must pass img1_path input"}

    if img2_path is None:
        return {"message": "you must pass img2_path input"}

    img1_data = base64.b64decode(img1_path)
    img2_data = base64.b64decode(img2_path)

    img1_np = np.frombuffer(img1_data, np.uint8)
    img2_np = np.frombuffer(img2_data, np.uint8)

    img1_cv2 = cv2.imdecode(img1_np, cv2.IMREAD_COLOR)
    img2_cv2 = cv2.imdecode(img2_np, cv2.IMREAD_COLOR)

    model_name = input_args.get("model_name", "VGG-Face")
    detector_backend = input_args.get("detector_backend", "opencv")
    enforce_detection = input_args.get("enforce_detection", True)
    distance_metric = input_args.get("distance_metric", "cosine")
    align = input_args.get("align", True)

    verification = service.verify(
        img1_path=img1_cv2,
        img2_path=img2_cv2,
        model_name=model_name,
        detector_backend=detector_backend,
        distance_metric=distance_metric,
        align=align,
        enforce_detection=enforce_detection,
    )

    verification["verified"] = str(verification["verified"])

    return verification


@blueprint.route("/checknip", methods=["POST"])
def checknip():
    input_args = request.get_json()

    if input_args is None:
        return {"message": "isian tidak boleh kosong"}

    nip = input_args.get("nip")
    if nip is None:
        return {"message": "nip tidak boleh kosong"}

    mydb = db_connection.create_connection_master()
    connection_master = mydb.cursor()

    try:
        check_sql = "SELECT NIP FROM pegawai WHERE NIP = %s"
        connection_master.execute(check_sql, (nip,))
        existing_nip = connection_master.fetchone()
        if (existing_nip):
            mydb = db_connection.create_connection_pegawai()
            connection_pegawai = mydb.cursor()
            try:
                check_sql = "SELECT NIP, KODE_ABSEN FROM kode_absensi WHERE NIP = %s"
                connection_pegawai.execute(check_sql, (nip,))
                existing_nip = connection_pegawai.fetchone()
                if (existing_nip):
                    nip_value = existing_nip[0]
                    kode_absen_value = existing_nip[1]
                    try:
                        check_sql = "SELECT IMG_BASE64 FROM img_presensi WHERE NIP = %s"
                        connection_pegawai.execute(check_sql, (nip,))
                        img_presensi_data = connection_pegawai.fetchone()
                        if (img_presensi_data):
                            return jsonify({"success": "true", "message": "nip terdaftar", "gambar_from_database": img_presensi_data[0], "kode_absen": kode_absen_value, "status": "3"}), 200
                        else:
                            return jsonify({"success": "false", "message": "pegawai belum melakukan pendaftaran wajah", "kode_absen": kode_absen_value, "status": "2"}), 200
                    except Exception as e:
                        return jsonify({"success": "false", "message": "pengecekan database gambar gagal", "status": "0"}), 500
                    finally:
                        db_connection.close_connection(mydb)
                else:
                    insert_sql = "INSERT INTO kode_absensi (NIP, KODE_ABSEN) VALUES (%s, %s)"
                    kode_absen_sementara = uuid.uuid4().hex[:8]
                    insert_val = (nip, kode_absen_sementara)
                    connection_pegawai.execute(insert_sql, insert_val)
                    mydb.commit()
                    return jsonify({"success": "false", "message": "pegawai belum melakukan pendaftaran wajah", "kode_absen": kode_absen_sementara, "status": "2"}), 200
            except Exception as e:
                return jsonify({"success": "false", "message": "pengecekan kode absen gagal", "status": "0"}), 500
            finally:
                db_connection.close_connection(mydb)
        else:
            return jsonify({"success": "false", "message": "nip tidak ditemukan", "status": "1"}), 200
    except Exception as e:
        return jsonify({"success": "false", "message": "pengecekan nip gagal", "status": "0"}), 500
    finally:
        db_connection.close_connection(mydb)

# status
# 0 = response 500 / gagal terhubung ke server
# 1 = nip tidak ditemukan
# 2 = pegawai belum melakukan pendaftaran wajah
# 3 = finish / siap absen


@blueprint.route("/pendaftaran_wajah", methods=["POST"])
@jwt_required()
def pendaftaran_wajah():
    input_args = request.get_json()

    if input_args is None:
        return {"message": "isian tidak boleh kosong"}

    nip = input_args.get("nip")
    image_base64 = input_args.get("image_base64")
    if nip is None:
        return {"message": "nip tidak boleh kosong"}
    if image_base64 is None:
        return {"message": "gambar tidak boleh kosong"}

    mydb = db_connection.create_connection_pegawai()
    connection_pegawai = mydb.cursor()

    try:
        check_sql = "SELECT NIP FROM img_presensi WHERE NIP = %s"
        connection_pegawai.execute(check_sql, (nip,))
        existing_nip = connection_pegawai.fetchone()
        if (existing_nip):
            update_sql = "UPDATE img_presensi SET IMG_BASE64 = %s WHERE NIP = %s"
            update_val = (image_base64, nip)
            connection_pegawai.execute(update_sql, update_val)
            return jsonify({"success": "true", "message": "nip terdaftar", "gambar_from_database": image_base64, "status": "1"}), 200
        else:
            insert_sql = "INSERT INTO img_presensi (NIP, IMG_BASE64) VALUES (%s, %s)"
            insert_val = (nip, image_base64)
            connection_pegawai.execute(insert_sql, insert_val)
            mydb.commit()
            return jsonify({"success": "true", "message": "berhasil mendaftarkan wajah", "gambar_from_database": image_base64, "status": "1"}), 200
    except Exception as e:
        return jsonify({"success": "false", "message": "gagal mendaftarkan wajah", "status": "0"}), 500
    finally:
        db_connection.close_connection(mydb)

# status
# 1 = berhasil mendaftarkan wajah
# 0 = gagal mendaftarkan wajah


@blueprint.route("/absen", methods=["POST"])
@jwt_required()
def presensi():
    input_args = request.get_json()

    if input_args is None:
        return jsonify({"message": "Empty input set passed"})

    required_keys = ["KODE_MESIN", "KODE_ABSEN", "IO_MODE",
                     "VERIFY_MODE", "WORK_CODE", "STATUS"]
    missing_keys = [key for key in required_keys if key not in input_args]

    if missing_keys:
        return jsonify({"message": f"Missing keys: {', '.join(missing_keys)}"}), 400
    else:
        try:
            # Extract values from the input JSON
            kode_mesin = input_args["KODE_MESIN"]
            kode_absen = input_args["KODE_ABSEN"]
            io_mode = input_args["IO_MODE"]
            verify_mode = input_args["VERIFY_MODE"]
            work_kode = input_args["WORK_CODE"]
            status = input_args["STATUS"]

            mydb = db_connection.create_connection_pegawai()
            mycursor = mydb.cursor()

            current_datetime = datetime.now()
            formatted_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')
            insert_sql = "INSERT INTO presensi (KODE_MESIN, KODE_ABSEN,IO_MODE,VERIFY_MODE,WORK_CODE,WAKTU_PRESENSI,TANGGAL,STATUS) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            insert_val = (kode_mesin, kode_absen, io_mode, verify_mode,
                          work_kode, formatted_datetime, formatted_datetime, status)
            mycursor.execute(insert_sql, insert_val)

            # Insert kedua ke tabel kedua
            formatted_current_date = datetime.now().strftime('%Y-%m-%d')
            insert_sql_2 = "INSERT INTO log_absensi (KODE_ABSEN, TANGGAL_ABSEN,IO_MODE) VALUES (%s, %s, %s)"
            insert_val_2 = (kode_absen, formatted_current_date, io_mode)
            mycursor.execute(insert_sql_2, insert_val_2)
            mydb.commit()

            response_data = {
                "KODE_MESIN": kode_mesin,
                "KODE_ABSEN": kode_absen,
                "IO_MODE": io_mode,
                "VERIFY_MODE": verify_mode,
                "WORK_CODE": work_kode,
                "WAKTU_PRESENSI": formatted_datetime,
                "TANGGAL": formatted_datetime,
                "STATUS": status
            }
            return jsonify({"success": "true", "message": "berhasil absen", "status": "1", "data": response_data}), 200
        except Exception as e:
            return jsonify({"success": "false", "message": "Terjadi kesalahan saat insert absensi", "status": "0"}), 500
        finally:
            db_connection.close_connection(mydb)

# status
# 1 = berhasil absen
# 0 = gagal absen


@blueprint.route("/checabsensihariini", methods=["POST"])
@jwt_required()
def checabsensihariini():
    input_args = request.get_json()

    if input_args is None:
        return {"message": "isian tidak boleh kosong"}

    kode_absen = input_args.get("kode_absen")
    io_mode = input_args.get("io_mode")
    if kode_absen is None:
        return {"message": "kode absen tidak boleh kosong"}
    if io_mode is None:
        return {"message": "io_mode tidak boleh kosong"}

    mydb = db_connection.create_connection_pegawai()
    connection_pegawai = mydb.cursor()

    try:
        formatted_current_date = datetime.now().strftime('%Y-%m-%d')
        check_sql = "SELECT IO_MODE FROM log_absensi WHERE KODE_ABSEN = %s AND TANGGAL_ABSEN =%s AND IO_MODE = %s"
        connection_pegawai.execute(
            check_sql, (kode_absen, formatted_current_date, io_mode))
        existing_absen = connection_pegawai.fetchone()
        if (existing_absen):
            return jsonify({"success": "true", "message": "sudah absen untuk hari ini", "status": "2"}), 200
        else:
            return jsonify({"success": "false", "message": "belum absen", "status": "1"}), 200
    except Exception as e:
        return jsonify({"success": "false", "message": "Terjadi kesalahan saat pengecekan absensi", "status": "0"}), 500
    finally:
        db_connection.close_connection(mydb)

# status
# 0 = gagal terhubung
# 1 = belum absen
# 2 = sudah absen masuk / pulang
