-- メモリ使用量が負の行があったら失敗
select *
from {{ ref('stg_process_metrics') }}
where memory_mb < 0
