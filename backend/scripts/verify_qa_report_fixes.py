import sys, os
sys.path.insert(0, os.path.abspath('backend'))
from app import create_app, db
from app.infrastructure.database.models.models import User, Role, Organization, OrgApiKey
from flask_jwt_extended import create_access_token

app = create_app()
with app.app_context():
    client = app.test_client()
    
    # 1. Test Admin & Team Member tokens
    adm_user = User.query.filter(User.email.like('%admin%')).first()
    tm_user = User.query.filter(User.role.has(name='Team Member')).first()
    
    adm_token = create_access_token(identity=str(adm_user.id), additional_claims={'session_id': 'TEST-SESS-ADM', 'role': adm_user.role.name, 'org_id': adm_user.org_id})
    tm_token = create_access_token(identity=str(tm_user.id), additional_claims={'session_id': 'TEST-SESS-TM', 'role': tm_user.role.name, 'org_id': tm_user.org_id})
    
    print(f'Admin user: {adm_user.email} (Role: {adm_user.role.name})')
    print(f'TM user: {tm_user.email} (Role: {tm_user.role.name})')
    
    # Test BLK-01: API Key Endpoint
    h_tm = {'Authorization': f'Bearer {tm_token}'}
    h_adm = {'Authorization': f'Bearer {adm_token}'}
    
    r_tm_key = client.get('/api/admin/integrations/api-key', headers=h_tm)
    r_adm_key = client.get('/api/admin/integrations/api-key', headers=h_adm)
    print(f'BLK-01 API Key GET -> TM status: {r_tm_key.status_code} (Expect 403), Admin status: {r_adm_key.status_code} (Expect 200)')
    assert r_tm_key.status_code == 403, 'BLK-01 Failed: TM could access API key endpoint'
    assert r_adm_key.status_code == 200, 'BLK-01 Failed: Admin could not access API key endpoint'
    
    # Check masking if key exists
    data = r_adm_key.get_json()
    if data and data.get('api_key'):
        masked = data.get('api_key')
        print(f'BLK-01 Masked key: {masked}')
        assert '***' in masked, 'BLK-01 Failed: Key not masked'
    else:
        print('BLK-01: No API key generated yet for this org. Let us generate one and test masking.')
        gen_res = client.post('/api/admin/integrations/api-key/generate', headers=h_adm)
        get_res = client.get('/api/admin/integrations/api-key', headers=h_adm)
        masked = get_res.get_json().get('api_key')
        print('Generated & fetched masked key:', masked)
        assert '***' in masked, 'BLK-01 Masking check failed'
        
    # Test BLK-02: Settings permission
    r_tm_set = client.put('/api/admin/org-settings', headers=h_tm, json={'organization_name': 'Hacked'})
    print(f'BLK-02 Settings PUT -> TM status: {r_tm_set.status_code} (Expect 403)')
    assert r_tm_set.status_code == 403, 'BLK-02 Failed: TM could update org-settings'

    # Test BLK-03: Audit Heartbeat
    r_hb = client.post('/api/admin/audit/heartbeat', headers=h_adm, json={'status': 'ok'})
    print(f'BLK-03 Audit Heartbeat POST -> Admin status: {r_hb.status_code} (Expect 200)')
    assert r_hb.status_code == 200, f'BLK-03 Failed: {r_hb.status_code} {r_hb.get_json()}'

    # Test BLK-04: HTML Route Guard for all roles
    # 1) Team Member accessing admin page -> 302 unauthorized
    client.set_cookie('access_token_cookie', tm_token)
    r_page_tm = client.get('/admin/users.html')
    print(f'BLK-04 Admin Page GET with TM Cookie -> status: {r_page_tm.status_code}, Location: {r_page_tm.headers.get("Location")}')
    assert r_page_tm.status_code == 302, 'BLK-04 Failed: TM was not redirected from admin page'
    assert 'reason=unauthorized' in r_page_tm.headers.get('Location', ''), 'BLK-04 redirect location incorrect'
    
    # 2) Admin accessing admin page -> 200
    client.set_cookie('access_token_cookie', adm_token)
    r_page_adm = client.get('/admin/users.html')
    print(f'BLK-04 Admin Page GET with Admin Cookie -> status: {r_page_adm.status_code}')
    assert r_page_adm.status_code in (200, 304), f'BLK-04 Admin Page status: {r_page_adm.status_code}'

    # 3) Facilitator accessing CEO dashboard -> 302 unauthorized
    fac_user = User.query.filter(User.role.has(name='Facilitator')).first()
    if fac_user:
        fac_token = create_access_token(identity=str(fac_user.id), additional_claims={'session_id': 'TEST-SESS-FAC', 'role': 'Facilitator', 'org_id': fac_user.org_id})
        client.set_cookie('access_token_cookie', fac_token)
        r_ceo_by_fac = client.get('/dashboard/dashboard-ceo.html')
        print(f'BLK-04 CEO Dashboard GET with Facilitator Cookie -> status: {r_ceo_by_fac.status_code}, Location: {r_ceo_by_fac.headers.get("Location")}')
        assert r_ceo_by_fac.status_code == 302 and 'reason=unauthorized' in r_ceo_by_fac.headers.get('Location', ''), 'BLK-04 Failed: Facilitator accessed CEO dashboard'
    
    client.delete_cookie('access_token_cookie')

    # Test BLK-05: Plant and Department Stats
    r_tm_plants = client.get('/api/admin/plants', headers=h_tm)
    r_adm_plants = client.get('/api/admin/plants', headers=h_adm)
    print(f'BLK-05 Plants GET -> TM status: {r_tm_plants.status_code} (Expect 403), Admin: {r_adm_plants.status_code} (Expect 200)')
    assert r_tm_plants.status_code == 403, 'BLK-05 Failed: TM accessed plants'
    assert r_adm_plants.status_code == 200, 'BLK-05 Failed: Admin could not access plants'

    r_tm_deps = client.get('/api/admin/departments', headers=h_tm)
    r_adm_deps = client.get('/api/admin/departments', headers=h_adm)
    print(f'BLK-05 Depts GET -> TM status: {r_tm_deps.status_code} (Expect 403), Admin: {r_adm_deps.status_code} (Expect 200)')
    assert r_tm_deps.status_code == 403, 'BLK-05 Failed: TM accessed departments'
    assert r_adm_deps.status_code == 200, 'BLK-05 Failed: Admin could not access departments'

    print('\n========================================')
    print('ALL BLK-01 to BLK-05 CHECKS PASSED 100%!')
    print('========================================')
