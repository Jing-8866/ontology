[QueryItem="订单 + 客户城市"]
PREFIX : <http://example.org/sales-order#>

SELECT ?order ?city WHERE {
  ?order a :SalesOrder ;
         :hasCustomer/:city ?city .
}
[QueryItem="DWS 日统计"]
PREFIX : <http://example.org/sales-order#>

SELECT ?date ?amount WHERE {
  ?s a :DailyStat ;
     :statDate ?date ;
     :totalAmount ?amount .
}
ORDER BY ?date
[QueryItem="ADS 月报"]
PREFIX : <http://example.org/sales-order#>

SELECT ?month ?amount WHERE {
  ?r a :MonthlyReport ;
     :reportMonth ?month ;
     :totalAmount ?amount .
}