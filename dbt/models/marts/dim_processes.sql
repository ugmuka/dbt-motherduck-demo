with

process_metrics as (

    select * from {{ ref('stg_process_metrics') }}

),

process_category as (

    select * from {{ ref('process_category') }}

),

-- 一度でも収集されたプロセス名の一覧
process_names as (

    select
        process_name,
        min(collected_at) as first_collected_at,
        max(collected_at) as last_collected_at

    from process_metrics
    group by 1

),

-- カテゴリはマスタから引く。マスタにない名前は落とさずに other にする
final as (

    select
        {{ dbt_utils.generate_surrogate_key(['process_names.process_name']) }} as process_key,
        process_names.process_name,
        coalesce(process_category.category, 'other') as category,
        process_category.process_name is not null as is_categorized,
        process_names.first_collected_at,
        process_names.last_collected_at

    from process_names
    left join process_category
        on process_names.process_name = process_category.process_name

)

select * from final
