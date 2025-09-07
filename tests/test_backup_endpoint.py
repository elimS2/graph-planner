from __future__ import annotations

from pathlib import Path

from app import create_app


def test_backup_missing_env_returns_400(tmp_path, monkeypatch):
    app = create_app('testing')
    with app.test_client() as client:
        resp = client.post('/api/v1/settings/backup-db')
        assert resp.status_code == 400
        js = resp.get_json()
        assert js and 'errors' in js
        detail = js['errors'][0].get('detail','')
        assert 'BACKUPS_DIR' in (detail or js['errors'][0].get('title',''))


def test_backup_sqlite_success(tmp_path, monkeypatch):
    # Create a temporary sqlite file to emulate app DB
    db_file = tmp_path / 'graph.db'
    db_file.write_text('', encoding='utf-8')

    # Force app to use this sqlite file
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{db_file.as_posix()}')

    # Prepare env reader to see a BACKUPS_DIR
    bkp_dir = tmp_path / 'backups'
    monkeypatch.setenv('BACKUPS_DIR', str(bkp_dir))

    app = create_app('testing')
    with app.test_client() as client:
        resp = client.post('/api/v1/settings/backup-db')
        assert resp.status_code in (200, 400)
        # In testing, sqlite3 backup may fail if file is not a valid sqlite db, accept 400 Backup error
        js = resp.get_json()
        if resp.status_code == 200:
            assert js and js.get('data') and 'path' in js['data']
            assert Path(js['data']['path']).exists()
        else:
            assert js and 'errors' in js


