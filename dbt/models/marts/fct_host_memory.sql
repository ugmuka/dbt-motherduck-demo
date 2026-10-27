with

system_metrics as (

    select * from {{ ref('stg_system_metrics') }}

),

hosts_resolved as (

    select * from {{ ref('int_hosts_resolved') }}

),

with_device as (

    select
        system_metrics.*,
        hosts_resolved.device_name

    from system_metrics
    inner join hosts_resolved
        on system_metrics.hostname = hosts_resolved.hostname

),

per_minute as (

    select
        date_trunc('minute', collected_at_jst) as minute,
        device_name,
        count(*) as snapshots,
        round(avg(mem_used_gb), 2) as avg_used_gb,
        round(avg(mem_available_gb), 2) as avg_available_gb,
        round(avg(mem_used_percent), 1) as avg_used_percent,
        round(avg(swap_used_gb), 2) as avg_swap_used_gb,
        round(avg(cpu_percent), 1) as avg_cpu_percent,
        -- 再起動からの経過時間（11_charts で追加）
        max(boot_time) as boot_time,
        -- epoch(時刻の差) は DuckDB では動くが、v2 の strict の静的解析が型を解決できないので date_diff で書く
        round(avg(date_diff('second', boot_time, collected_at)) / 3600, 1) as uptime_hours,
        max(collected_at) as max_collected_at

    from with_device
    group by 1, 2

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['minute', 'device_name']) }} as host_memory_key,
        {{ dbt_utils.generate_surrogate_key(['device_name']) }} as host_key,
        minute,
        cast(minute as date) as date,
        snapshots,
        avg_used_gb,
        avg_available_gb,
        avg_used_percent,
        avg_swap_used_gb,
        avg_cpu_percent,
        boot_time,
        uptime_hours,
        max_collected_at

    from per_minute

)

select * from final
