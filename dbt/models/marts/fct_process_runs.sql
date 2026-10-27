with

process_metrics as (

    select * from {{ ref('stg_process_metrics') }}

),

hosts_resolved as (

    select * from {{ ref('int_hosts_resolved') }}

),

with_device as (

    select
        process_metrics.*,
        hosts_resolved.device_name

    from process_metrics
    inner join hosts_resolved
        on process_metrics.hostname = hosts_resolved.hostname

),

-- プロセスの 1 回の起動を (PC, pid, 起動時刻) で見分ける。pid は使い回されるので起動時刻と組にする
runs as (

    select
        device_name,
        pid,
        create_time,
        min(process_name) as process_name,
        min(collected_at) as first_seen_at,
        max(collected_at) as last_seen_at,
        count(*) as snapshots

    from with_device
    where create_time is not null
    group by 1, 2, 3

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['device_name', 'pid', 'epoch_us(create_time)']) }} as process_run_key,
        {{ dbt_utils.generate_surrogate_key(['device_name']) }} as host_key,
        {{ dbt_utils.generate_surrogate_key(['process_name']) }} as process_key,
        create_time as started_at,
        create_time at time zone 'Asia/Tokyo' as started_at_jst,
        first_seen_at,
        last_seen_at,
        snapshots,
        -- 収集を始める前から動いていたプロセスは「起動件数」に数えない
        create_time >= min(first_seen_at) over (partition by device_name) as is_started_while_collecting,
        -- 起動から最後に見えた時刻までの観測時間。まだ動いているプロセスは下限になる
        round(date_diff('second', create_time, last_seen_at) / 60, 1) as observed_lifetime_minutes

    from runs

)

select * from final
