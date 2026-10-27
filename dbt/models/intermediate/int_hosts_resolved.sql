with

system_metrics as (

    select * from {{ ref('stg_system_metrics') }}

),

host_aliases as (

    select * from {{ ref('host_aliases') }}

),

hostnames as (

    select distinct hostname from system_metrics

),

-- 対応表に載っていないホスト名は、そのまま PC 名として扱う
resolved as (

    select
        hostnames.hostname,
        coalesce(host_aliases.device_name, hostnames.hostname) as device_name,
        host_aliases.hostname is not null as is_aliased

    from hostnames
    left join host_aliases
        on hostnames.hostname = host_aliases.hostname

)

select * from resolved
