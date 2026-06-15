from flask import Flask, request, jsonify
import requests
import re
import time
import random
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Proxy list - ONLY for Parivahan
PROXIES = [
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_14068911_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_76090875_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_55959051_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_20782905_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_15476846_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_55677753_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_36922492_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_58760767_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_25856756_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_18064269_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_90704531_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_80377955_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_91038744_time_15:4318888@change5.owlproxy.com:7778",
]

SMC_HOMEPAGE = "https://www.smcinsurance.com/"
SMC_API = "https://www.smcinsurance.com/central/centralcall/CallReqWithHeader"

HOMEPAGE_URL = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/statevalidation/homepage.xhtml?statecd=Mzc2MzM2MzAzNjY0MzIzODM3NjIzNjY0MzY2MjM3NDQ0Yw=="
HOMEPAGE_BASE = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/statevalidation/homepage.xhtml"
LOGIN_URL = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/usermgmt/login.xhtml"
FORM_URL = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/balanceservice/form_reschedule_fitness.xhtml"

def get_random_proxy():
    """Get a random proxy from the list"""
    return random.choice(PROXIES) if PROXIES else None

def create_session(use_proxy=False):
    """
    Create a session
    use_proxy=False for SMC (direct connection)
    use_proxy=True for Parivahan (proxy needed)
    """
    session = requests.Session()
    retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    
    if use_proxy:
        proxy = get_random_proxy()
        session.proxies = {
            'http': proxy,
            'https': proxy
        }
    
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    })
    return session

def get_vehicle_details_from_smc(vehicle_number):
    """
    Get vehicle details from SMC API
    NO PROXY - Direct connection
    """
    try:
        # Direct connection to SMC (no proxy)
        with create_session(use_proxy=False) as s:
            home = s.get(SMC_HOMEPAGE, timeout=15, verify=False)
            home.raise_for_status()

            mcbc_cookie = s.cookies.get("MCBC")

            if not mcbc_cookie:
                return {"success": False, "error": "MCBC cookie not found"}

            payload = {
                "url": "GetVaahanDetailsByVehicleNo",
                "props": [
                    vehicle_number,
                    "",
                    "0"
                ]
            }

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "okhttp/4.9.2",
                "Cookie": f"MCBC={mcbc_cookie}"
            }

            response = s.post(
                SMC_API,
                headers=headers,
                json=payload,
                timeout=15,
                verify=False
            )

            response.raise_for_status()
            data = response.json()

            if data.get("statusCode") == 200:
                vehicle_data = data.get("response", {})
                chassis = vehicle_data.get("chassis", "").replace(" ", "")
                mobile_no = vehicle_data.get("mobile_no", "")

                if len(chassis) >= 5:
                    return {
                        "success": True,
                        "chassis_last_5": chassis[-5:],
                        "mobile_no": mobile_no,
                        "vehicle_data": vehicle_data
                    }
                return {"success": False, "error": "Chassis too short or not found"}

            return {"success": False, "error": "SMC API returned no data"}

    except Exception as e:
        return {"success": False, "error": f"SMC Error: {str(e)}"}

def extract_viewstate(html):
    """Extract ViewState from HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    vs = soup.find('input', {'name': 'javax.faces.ViewState'})
    return vs.get('value') if vs else None

def extract_viewstate_from_ajax(text):
    """Extract ViewState from AJAX response"""
    m = re.search(r'<update id="j_id1:javax.faces.ViewState:0"><!\[CDATA\[(.*?)\]\]></update>', text)
    return m.group(1) if m else None

def find_checkbox_id(html):
    """Find checkbox ID in HTML"""
    m = re.search(r'<div[^>]*id="(j_idt\d+)"[^>]*class="[^"]*ui-chkbox', html)
    if not m:
        m = re.search(r'PrimeFaces.cw("SelectBooleanCheckbox"[^}]*id:"(j_idt\d+)"', html)
    return m.group(1) if m else "j_idt193"

def fetch_mobile_number(vehicle_number, chassis_last_5, fallback_mobile=""):
    """
    Fetch mobile number from Parivahan portal
    WITH PROXY - Parivahan blocks foreign IPs
    """
    # Use proxy for Parivahan
    session = create_session(use_proxy=True)

    ajax_headers = {
        'Accept': 'application/xml, text/xml, */*; q=0.01',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Faces-Request': 'partial/ajax',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://vahan.parivahan.gov.in',
    }

    for attempt in range(2):
        try:
            # Step 1: Get homepage
            r1 = session.get(HOMEPAGE_URL, timeout=30, verify=False)
            if r1.status_code != 200:
                continue
            viewstate = extract_viewstate(r1.text)
            if not viewstate:
                continue

            checkbox_id = find_checkbox_id(r1.text)
            ajax_headers['Referer'] = HOMEPAGE_URL

            # Step 2: Office selection
            r2 = session.post(HOMEPAGE_BASE, data={
                'javax.faces.partial.ajax': 'true',
                'javax.faces.source': 'fit_c_office_to',
                'javax.faces.partial.execute': 'fit_c_office_to',
                'javax.faces.behavior.event': 'change',
                'javax.faces.partial.event': 'change',
                'homepageformid': 'homepageformid',
                'fit_c_office_to_input': '1',
                'javax.faces.ViewState': viewstate,
            }, headers=ajax_headers, timeout=30, verify=False)
            viewstate = extract_viewstate_from_ajax(r2.text) or viewstate

            # Step 3: Checkbox
            r3 = session.post(HOMEPAGE_BASE, data={
                'javax.faces.partial.ajax': 'true',
                'javax.faces.source': checkbox_id,
                'javax.faces.partial.execute': checkbox_id,
                'javax.faces.partial.render': 'proccedHomeButtonId',
                'javax.faces.behavior.event': 'change',
                'homepageformid': 'homepageformid',
                f'{checkbox_id}_input': 'on',
                'javax.faces.ViewState': viewstate,
            }, headers=ajax_headers, timeout=30, verify=False)
            viewstate = extract_viewstate_from_ajax(r3.text) or viewstate

            # Step 4: Proceed button
            r4 = session.post(HOMEPAGE_BASE, data={
                'javax.faces.partial.ajax': 'true',
                'javax.faces.source': 'proccedHomeButtonId',
                'javax.faces.partial.execute': '@all',
                'proccedHomeButtonId': 'proccedHomeButtonId',
                'homepageformid': 'homepageformid',
                f'{checkbox_id}_input': 'on',
                'javax.faces.ViewState': viewstate,
            }, headers=ajax_headers, timeout=30, verify=False)
            viewstate = extract_viewstate_from_ajax(r4.text) or viewstate

            # Step 5: Dialog button
            dialog_match = re.search(r'id="(j_idt\d+)"[^>]*class="[^"]*ui-button', r4.text)
            dialog_btn = dialog_match.group(1) if dialog_match else "j_idt536"
            r5 = session.post(HOMEPAGE_BASE, data={
                'javax.faces.partial.ajax': 'true',
                'javax.faces.source': dialog_btn,
                'javax.faces.partial.execute': '@all',
                f'{dialog_btn}': dialog_btn,
                'homepageformid': 'homepageformid',
                f'{checkbox_id}_input': 'on',
                'javax.faces.ViewState': viewstate,
            }, headers=ajax_headers, timeout=30, verify=False)
            viewstate = extract_viewstate_from_ajax(r5.text) or viewstate

            # Step 6: Login page
            r6 = session.get(LOGIN_URL + "?faces-redirect=true", timeout=30, verify=False)
            viewstate = extract_viewstate(r6.text)
            if not viewstate:
                continue

            # Step 7: Login
            fit_match = re.search(r'id="(j_idt\d+)"[^>]*name="\1"[^>]*type="submit"', r6.text)
            fit_btn = fit_match.group(1) if fit_match else "j_idt506"
            post_headers = {
                **session.headers,
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://vahan.parivahan.gov.in',
                'Referer': LOGIN_URL + "?faces-redirect=true",
            }
            r7 = session.post(LOGIN_URL, data={
                'loginForm': 'loginForm',
                f'{fit_btn}': fit_btn,
                'javax.faces.ViewState': viewstate,
                'fitbalcTest': 'fitbalcTest',
                'pur_cd': '86',
            }, headers=post_headers, timeout=30, verify=False)

            # Step 8: Form page
            form_headers = {**session.headers, 'Referer': LOGIN_URL + "?faces-redirect=true"}
            r8 = session.get(FORM_URL, headers=form_headers, timeout=30, verify=False)
            viewstate = extract_viewstate(r8.text)
            if not viewstate:
                continue

            # Step 9: Validate details
            ajax_headers['Referer'] = FORM_URL
            r9 = session.post(FORM_URL, data={
                'javax.faces.partial.ajax': 'true',
                'javax.faces.source': 'balanceFeesFine:validate_dtls',
                'javax.faces.partial.execute': '@all',
                'javax.faces.partial.render': 'balanceFeesFine:auth_panel',
                'balanceFeesFine:validate_dtls': 'balanceFeesFine:validate_dtls',
                'balanceFeesFine': 'balanceFeesFine',
                'balanceFeesFine:tf_reg_no': vehicle_number,
                'balanceFeesFine:tf_chasis_no': chassis_last_5,
                'javax.faces.ViewState': viewstate,
            }, headers=ajax_headers, timeout=30, verify=False)

            text = r9.text

            # Find mobile number
            for pat in [r'id="balanceFeesFine:tf_mobile"[^>]*value="(\d{10})"',
                        r'value="(\d{10})"[^>]*id="balanceFeesFine:tf_mobile"',
                        r'balanceFeesFine:tf_mobile[^>]*value="(\d{10})"']:
                m = re.search(pat, text, re.DOTALL)
                if m and m.group(1)[0] in '6789':
                    return {"success": True, "mobile_number": m.group(1)}

            fallback = re.findall(r'\b[6-9]\d{9}\b', text)
            if fallback:
                return {"success": True, "mobile_number": fallback[0]}

        except Exception as e:
            print(f"Parivahan attempt {attempt+1}: {str(e)[:100]}")

        if attempt == 0:
            time.sleep(2)

    # Return SMC mobile as fallback
    if fallback_mobile and len(fallback_mobile) == 10 and fallback_mobile[0] in '6789':
        return {"success": True, "mobile_number": fallback_mobile}

    return {"success": False, "error": "Mobile number not found"}

@app.route("/fetch", methods=["GET"])
def fetch_contact():
    """Main endpoint"""
    vehicle_number = request.args.get("vehicle_number", "").strip().upper()
    vehicle_number = re.sub(r'[^A-Z0-9]', '', vehicle_number)

    if not vehicle_number or len(vehicle_number) < 6 or len(vehicle_number) > 12:
        return jsonify({"success": False, "error": "Invalid vehicle number"}), 400

    # Step 1: Get chassis from SMC (Direct connection - no proxy)
    smc_result = get_vehicle_details_from_smc(vehicle_number)

    if not smc_result["success"]:
        return jsonify(smc_result), 400

    # Step 2: Get mobile from Parivahan (With proxy)
    mobile_result = fetch_mobile_number(
        vehicle_number,
        smc_result["chassis_last_5"],
        smc_result.get("mobile_no", "")
    )

    mobile = None
    if mobile_result["success"]:
        mobile = mobile_result["mobile_number"]
    elif smc_result.get("mobile_no"):
        mobile = smc_result["mobile_no"]

    if mobile:
        vehicle_data = smc_result.get("vehicle_data", {})
        vehicle_data["mobile_no"] = mobile
        vehicle_data.pop("transKey", None)
        return jsonify({
            "statusCode": 200,
            "response": vehicle_data
        })

    return jsonify({"success": False, "error": mobile_result.get("error", "Failed to get mobile")}), 400

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "running",
        "message": "Vehicle Insurance Contact Fetcher API",
        "endpoint": "/fetch?vehicle_number=MH12AB1234",
        "note": "SMC: Direct, Parivahan: Proxy"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
