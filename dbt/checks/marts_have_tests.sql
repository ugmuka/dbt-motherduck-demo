-- marts のモデルにはテストを 1 本以上付ける（主キーの unique / not_null が最低限）
select m.unique_id
from {{ info_schema('models') }} as m
where m.enabled
  and m.package_name = (select project_name from {{ info_schema('project') }})
  and m.original_file_path like 'models/marts/%'
  and not exists (
    select 1
    from {{ info_schema('data_tests') }} as t
    where t.enabled and t.node_unique_id = m.unique_id
  )
