-- marts のモデルには description を必ず書く（ダッシュボードの利用者が読むので）
select unique_id
from {{ info_schema('models') }}
where enabled
  and package_name = (select project_name from {{ info_schema('project') }})
  and original_file_path like 'models/marts/%'
  and coalesce(description, '') = ''
