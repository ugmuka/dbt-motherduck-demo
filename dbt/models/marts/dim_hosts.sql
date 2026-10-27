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

-- PC ごとに最新の収集を 1 行選ぶ（物理メモリや起動時刻は最新の値を使う）
latest as (

    select * from with_device
    qualify row_number() over (partition by device_name order by collected_at desc) = 1

),

collected_range as (

    select
        device_name,
        -- この PC がこれまでに名乗ったホスト名
        string_agg(distinct hostname, ', ' order by hostname) as hostnames,
        count(distinct hostname) as hostname_count,
        min(collected_at) as first_collected_at,
        max(collected_at) as last_collected_at

    from with_device
    group by 1

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['latest.device_name']) }} as host_key,
        latest.device_name,
        latest.hostname as last_hostname,
        collected_range.hostnames,
        collected_range.hostname_count,
        latest.mem_total_gb,
        latest.boot_time as last_boot_time,
        collected_range.first_collected_at,
        collected_range.last_collected_at

    from latest
    inner join collected_range
        on latest.device_name = collected_range.device_name

)

select * from final
