with

process_metrics as (

    select * from {{ ref('stg_process_metrics') }}

),

hosts_resolved as (

    select * from {{ ref('int_hosts_resolved') }}

),

-- ホスト名を PC 名に寄せる（Mac はホスト名が変わるため）
with_device as (

    select
        process_metrics.*,
        hosts_resolved.device_name

    from process_metrics
    inner join hosts_resolved
        on process_metrics.hostname = hosts_resolved.hostname

),

-- 1 回の収集の中で、同名プロセス（Chrome の Helper など）を合算して 1 行にする
per_snapshot as (

    select
        collected_at,
        collected_at_jst,
        device_name,
        process_name,
        count(*) as process_count,
        -- 終了したのに親に回収されずに残っているプロセス（11_charts で追加）
        count(*) filter (where status = 'zombie') as zombie_count,
        sum(memory_mb) as memory_mb,
        sum(cpu_percent) as cpu_percent

    from with_device
    group by 1, 2, 3, 4

),

-- 合算した値を 1 分の中で平均する。順序を逆にするとプロセス 1 個あたりの平均になってしまう
per_minute as (

    select
        date_trunc('minute', collected_at_jst) as minute,
        device_name,
        process_name,
        count(*) as snapshots,
        round(avg(process_count), 1) as avg_process_count,
        round(avg(zombie_count), 1) as avg_zombie_count,
        round(avg(memory_mb), 1) as avg_memory_mb,
        round(max(memory_mb), 1) as max_memory_mb,
        round(avg(cpu_percent), 1) as avg_cpu_percent,
        -- freshness の判定用（UTC のまま）
        max(collected_at) as max_collected_at

    from per_snapshot
    group by 1, 2, 3

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['minute', 'device_name', 'process_name']) }} as process_memory_key,
        {{ dbt_utils.generate_surrogate_key(['device_name']) }} as host_key,
        {{ dbt_utils.generate_surrogate_key(['process_name']) }} as process_key,
        minute,
        cast(minute as date) as date,
        snapshots,
        avg_process_count,
        avg_zombie_count,
        avg_memory_mb,
        max_memory_mb,
        avg_cpu_percent,
        max_collected_at

    from per_minute

)

select * from final
