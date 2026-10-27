{{ config(
    materialized='incremental',
    unique_key=['collected_at', 'hostname'],
    incremental_strategy='delete+insert'
) }}

with

source as (

    select source.*
    from {{ source('raw', 'system_metrics') }} as source
    {% if is_incremental() %}
    -- stg_process_metrics と同じく、ホストごとの前回最大時刻より新しい行だけ
    left join (
        select hostname, max(collected_at) as max_collected_at
        from {{ this }}
        group by 1
    ) as loaded
        on source.hostname = loaded.hostname
    where source.collected_at > coalesce(loaded.max_collected_at, '1970-01-01'::timestamptz)
    {% endif %}

),

renamed as (

    select
        -- ids
        hostname,

        -- numerics
        round(mem_total / 1024.0 / 1024 / 1024, 2) as mem_total_gb,
        round(mem_used / 1024.0 / 1024 / 1024, 2) as mem_used_gb,
        round(mem_available / 1024.0 / 1024 / 1024, 2) as mem_available_gb,
        mem_percent as mem_used_percent,
        round(swap_used / 1024.0 / 1024 / 1024, 2) as swap_used_gb,
        cpu_percent,

        -- timestamps
        collected_at,
        collected_at at time zone 'Asia/Tokyo' as collected_at_jst,
        boot_time,
        date_diff('hour', boot_time, collected_at) as uptime_hours

    from source

),

deduplicated as (

    select * from renamed
    qualify row_number() over (partition by collected_at, hostname) = 1

)

select * from deduplicated
