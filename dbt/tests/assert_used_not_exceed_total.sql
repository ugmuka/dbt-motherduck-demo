-- 使用メモリが物理メモリの合計を超えていたら失敗
select *
from {{ ref('stg_system_metrics') }}
where mem_used_gb > mem_total_gb
