import re
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import json

BASE_URL = "http://127.0.0.1:8000"

def run_live_tests():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    print("[1] Testing GET /login/")
    req = urllib.request.Request(f"{BASE_URL}/login/")
    with opener.open(req) as res:
        html = res.read().decode('utf-8')
        assert res.status == 200
        csrf_match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', html)
        assert csrf_match, "CSRF middleware token not found on login page"
        csrf_token = csrf_match.group(1)
        print("  -> Login page loaded successfully. CSRF extracted.")

    print("[2] Testing POST /login/ (Sign in as demo)")
    login_data = urllib.parse.urlencode({
        'username': 'demo',
        'password': 'DemoPassword123!',
        'csrfmiddlewaretoken': csrf_token,
    }).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/login/", data=login_data, headers={'Referer': f"{BASE_URL}/login/"})
    with opener.open(req) as res:
        final_url = res.geturl()
        html = res.read().decode('utf-8')
        print(f"  -> Redirected to: {final_url}")
        assert 'Welcome to Google Drive' in html or 'Work Projects' in html or 'My Drive' in html
        print("  -> Authenticated session active!")

    # Extract new CSRF token from cookies or HTML
    csrf_token = None
    for cookie in cj:
        if cookie.name == 'csrftoken':
            csrf_token = cookie.value
    assert csrf_token, "Session csrftoken cookie found"

    print("[3] Testing API: Create folder via /api/folders/create/")
    folder_data = urllib.parse.urlencode({'name': 'Live Script Test Folder'}).encode('utf-8')
    req = urllib.request.Request(
        f"{BASE_URL}/api/folders/create/",
        data=folder_data,
        headers={'X-CSRFToken': csrf_token, 'Referer': BASE_URL}
    )
    with opener.open(req) as res:
        data = json.loads(res.read().decode('utf-8'))
        assert data['success'] is True
        created_folder_id = data['item']['id']
        print(f"  -> Created folder: {created_folder_id} - '{data['item']['name']}'")

    print("[4] Testing API: Rename folder via /api/items/<id>/rename/")
    rename_data = urllib.parse.urlencode({'name': 'Renamed Live Folder'}).encode('utf-8')
    req = urllib.request.Request(
        f"{BASE_URL}/api/items/{created_folder_id}/rename/",
        data=rename_data,
        headers={'X-CSRFToken': csrf_token, 'Referer': BASE_URL}
    )
    with opener.open(req) as res:
        data = json.loads(res.read().decode('utf-8'))
        assert data['success'] is True
        assert data['item']['name'] == 'Renamed Live Folder'
        print(f"  -> Renamed to: {data['item']['name']}")

    print("[5] Testing API: Star item via /api/items/<id>/star/")
    req = urllib.request.Request(
        f"{BASE_URL}/api/items/{created_folder_id}/star/",
        data=b'',
        headers={'X-CSRFToken': csrf_token, 'Referer': BASE_URL}
    )
    with opener.open(req) as res:
        data = json.loads(res.read().decode('utf-8'))
        assert data['success'] is True
        assert data['is_starred'] is True
        print("  -> Item starred!")

    print("[6] Testing GET /drive/starred/")
    req = urllib.request.Request(f"{BASE_URL}/drive/starred/")
    with opener.open(req) as res:
        html = res.read().decode('utf-8')
        assert 'Renamed Live Folder' in html
        print("  -> Starred view confirmed!")

    print("[7] Testing API: Trash item via /api/items/<id>/trash/")
    req = urllib.request.Request(
        f"{BASE_URL}/api/items/{created_folder_id}/trash/",
        data=b'',
        headers={'X-CSRFToken': csrf_token, 'Referer': BASE_URL}
    )
    with opener.open(req) as res:
        data = json.loads(res.read().decode('utf-8'))
        assert data['success'] is True
        print("  -> Moved to bin!")

    print("[8] Testing GET /drive/trash/")
    req = urllib.request.Request(f"{BASE_URL}/drive/trash/")
    with opener.open(req) as res:
        html = res.read().decode('utf-8')
        assert 'Renamed Live Folder' in html
        print("  -> Trash view confirmed!")

    print("[9] Testing API: Restore item via /api/items/<id>/restore/")
    req = urllib.request.Request(
        f"{BASE_URL}/api/items/{created_folder_id}/restore/",
        data=b'',
        headers={'X-CSRFToken': csrf_token, 'Referer': BASE_URL}
    )
    with opener.open(req) as res:
        data = json.loads(res.read().decode('utf-8'))
        assert data['success'] is True
        print("  -> Item restored!")

    print("[10] Testing API: Permanent delete via /api/items/<id>/delete/")
    req = urllib.request.Request(
        f"{BASE_URL}/api/items/{created_folder_id}/delete/",
        data=b'',
        headers={'X-CSRFToken': csrf_token, 'Referer': BASE_URL}
    )
    with opener.open(req) as res:
        data = json.loads(res.read().decode('utf-8'))
        assert data['success'] is True
        print("  -> Item permanently deleted!")

    print("[11] Testing Instant Search API: GET /api/search/?q=Welcome")
    req = urllib.request.Request(f"{BASE_URL}/api/search/?q=Welcome")
    with opener.open(req) as res:
        assert res.status == 200
        data = json.loads(res.read().decode('utf-8'))
        assert 'results' in data
        assert len(data['results']) >= 1
        item_names = [r['name'] for r in data['results']]
        assert any('Welcome' in n for n in item_names)
        print(f"  -> Found search results: {item_names}")

    print("[12] Testing File Public Sharing & Inter-User Access")
    welcome_item = next(r for r in data['results'] if not r['is_folder'])
    share_item_id = welcome_item['id']

    # 12a: Enable sharing via API
    share_post_data = urllib.parse.urlencode({'is_shared': 'true'}).encode('utf-8')
    req = urllib.request.Request(
        f"{BASE_URL}/api/items/{share_item_id}/share/",
        data=share_post_data,
        headers={'X-CSRFToken': csrf_token, 'Referer': BASE_URL}
    )
    with opener.open(req) as res:
        assert res.status == 200
        share_res = json.loads(res.read().decode('utf-8'))
        assert share_res['success'] is True
        assert share_res['is_shared'] is True
        assert bool(share_res['share_url'])
        share_url = share_res['share_url']
        share_token = share_res['share_token']
        print(f"  -> Share enabled: {share_url}")

    # 12b: Anonymous access to share link
    anon_req = urllib.request.Request(share_url)
    with urllib.request.urlopen(anon_req) as res:
        assert res.status == 200
        html = res.read().decode('utf-8')
        assert welcome_item['name'] in html
        assert 'Download' in html
        print("  -> Anonymous visitor successfully viewed shared file!")

    # 12c: Anonymous file download
    dl_url = f"{BASE_URL}/drive/download/{share_item_id}/"
    with urllib.request.urlopen(dl_url) as res:
        assert res.status == 200
        content = res.read()
        assert len(content) > 0
        print(f"  -> Anonymous visitor successfully downloaded file ({len(content)} bytes)!")

    # 12d: Inter-user sharing (admin user opens demo's share link)
    admin_cj = http.cookiejar.CookieJar()
    admin_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(admin_cj))

    # Get admin login page CSRF
    with admin_opener.open(f"{BASE_URL}/login/") as res:
        html = res.read().decode('utf-8')
        m = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', html)
        admin_csrf = m.group(1)

    # Login as admin
    admin_login = urllib.parse.urlencode({
        'username': 'admin',
        'password': 'AdminPassword123!',
        'csrfmiddlewaretoken': admin_csrf,
    }).encode('utf-8')
    with admin_opener.open(urllib.request.Request(f"{BASE_URL}/login/", data=admin_login, headers={'Referer': f"{BASE_URL}/login/"})) as res:
        assert res.status == 200
        print("  -> Logged in as second user: 'admin'")

    admin_session_csrf = None
    for cookie in admin_cj:
        if cookie.name == 'csrftoken':
            admin_session_csrf = cookie.value

    # Admin visits demo's share link
    with admin_opener.open(share_url) as res:
        assert res.status == 200
        html = res.read().decode('utf-8')
        assert welcome_item['name'] in html
        assert 'Save to My Drive' in html
        print("  -> Logged-in 'admin' successfully viewed shared file with 'Save to My Drive'!")

    # Admin saves copy to own drive
    save_req = urllib.request.Request(
        f"{BASE_URL}/api/shared/save-copy/{share_item_id}/",
        data=b'',
        headers={'X-CSRFToken': admin_session_csrf, 'Referer': share_url}
    )
    with admin_opener.open(save_req) as res:
        assert res.status == 200
        save_data = json.loads(res.read().decode('utf-8'))
        assert save_data['success'] is True
        print(f"  -> 'admin' saved copy to their Drive: {save_data['message']}")

    # 12e: Revoke sharing and verify 404
    revoke_data = urllib.parse.urlencode({'is_shared': 'false'}).encode('utf-8')
    req = urllib.request.Request(
        f"{BASE_URL}/api/items/{share_item_id}/share/",
        data=revoke_data,
        headers={'X-CSRFToken': csrf_token, 'Referer': BASE_URL}
    )
    with opener.open(req) as res:
        assert res.status == 200
        revoke_res = json.loads(res.read().decode('utf-8'))
        assert revoke_res['is_shared'] is False
        print("  -> Revoked sharing")

    try:
        urllib.request.urlopen(share_url)
        assert False, "Should have raised 404 after revocation"
    except urllib.error.HTTPError as e:
        assert e.code == 404
        print("  -> Confirmed 404 blocked access after revocation!")

    print("\nALL LIVE SERVER TESTS (INCLUDING SEARCH AND SHARING) PASSED PERFECTLY!")

if __name__ == '__main__':
    run_live_tests()

