-- 層ごとの名前の決まり: staging は stg_、intermediate は int_、marts は fct_ か dim_
select unique_id
from {{ info_schema('models') }}
where enabled
  and package_name = (select project_name from {{ info_schema('project') }})
  and not (
    (original_file_path like 'models/staging/%' and name like 'stg\_%' escape '\')
    or (original_file_path like 'models/intermediate/%' and name like 'int\_%' escape '\')
    or (original_file_path like 'models/marts/%' and (name like 'fct\_%' escape '\' or name like 'dim\_%' escape '\'))
  )
