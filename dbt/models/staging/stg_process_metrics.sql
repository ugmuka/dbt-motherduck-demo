{{ config(
    materialized='incremental',
    unique_key='sample_key',
    incremental_strategy='delete+insert'
) }}

with

source as (

    select source.*
    from {{ source('raw', 'process_metrics') }} as source
    {% if is_incremental() %}
    -- ホストごとに「前回までに取り込んだ最後の時刻」より新しい行だけを処理する
    -- （ホストが複数あると、全体の max では遅れて届いたホストの行を取りこぼす）
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
        -- 時刻はタイムゾーンの表示形式に左右されない epoch（マイクロ秒）にしてからキーにする
        {{ dbt_utils.generate_surrogate_key(['epoch_us(collected_at)', 'hostname', 'pid']) }} as sample_key,
        hostname,
        pid,

        -- strings
        -- Mac と Windows で名前を揃える: 小文字にして、Windows の .exe を落とす
        regexp_replace(lower(trim(name)), '\.exe$', '') as process_name,
        status,
        username,

        -- numerics
        memory_rss as memory_bytes,
        round(memory_rss / 1024.0 / 1024.0, 1) as memory_mb,
        memory_percent,
        cpu_percent,
        num_threads,

        -- timestamps
        collected_at,
        -- 表示用の日本時間。UTC の collected_at は freshness と差分処理に使うので残す
        collected_at at time zone 'Asia/Tokyo' as collected_at_jst,
        create_time

    from source

),

deduplicated as (

    select * from renamed
    -- 今回の差分の中の重複はここで、取り込み済みの行との重複は unique_key + delete+insert で排除する
    qualify row_number() over (partition by collected_at, hostname, pid) = 1

)

select * from deduplicated
