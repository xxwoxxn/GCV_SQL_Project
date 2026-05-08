# GCV SQL Project

SQL 기반 데이터 분석 프로젝트입니다.

## 구조

```
GCV_SQL_Project/
├── ERD.png          # 테이블 관계도 (Entity-Relationship Diagram)
├── schema/          # 원본 데이터 CSV 파일
│   ├── Account.csv
│   ├── Customer.csv
│   ├── Invoice.csv
│   ├── Orders.csv
│   ├── Opportunity.csv
│   └── ...
└── README.md
```

## 데이터 구성

`schema/` 폴더에는 다음 도메인의 데이터가 포함되어 있습니다:

- **고객/계정**: Account, Customer, Role, JobTitle
- **영업**: Lead, LeadSource, LeadStatus, Opportunity, Stage
- **견적/주문**: Quote, QuoteLineItem, QuoteStatus, Orders, OrderStatus
- **청구/결제**: Invoice, PaymentMethod, PaymentStatus, BillingAddress
- **제품**: Product, FuelType, VehicleType, Warranty
- **기타**: Industry, LostReason, ShippingAddress, Users
