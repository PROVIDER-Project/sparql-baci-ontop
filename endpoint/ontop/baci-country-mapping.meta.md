# Country-link provenance

- Dataset: CEPII BACI HS92, V202601, packaging revision 1.
- Source coordinate: `org.aksw.data.thirdparty.fr.cepii.baci:HS92_V202601:1`.
- Source country classifier: `country_codes_V202601`, type `csv.zst`.
- Compressed country artifact SHA-256:
  `5f5061c2d2182fee781b78371c647ee833d6e92fc411b831933db946bf1bdcec`.
- Source product classifier: `product_codes_HS92_V202601`, type `csv.zst`.
- Compressed product artifact SHA-256:
  `6974461b362114162976df643313f51fb7706606dd604cc6292d87f12874be39`.
- Reviewed on: 2026-10-16.

The numeric area identifier and both ISO columns are read directly from the
country artifact. Country labels are not used to infer identities. Original
names and ISO columns are retained unchanged in the relational source table
and as BACI area metadata. Facts retain their original BACI area codes.

The local `baci-country-exclusions.csv` is an editorial eligibility policy,
not an official CEPII membership list. It prevents current-country identity
claims for historical territories, customs unions, and residuals. Remaining
source ISO3 strings matching `[A-Z]{3}` become shared country join targets.
Eligible ISO3s must be unique; a collision fails loading instead of arbitrarily
selecting one. The reviewed complete input produces 226 links and 12 omissions
from 238 source definitions. See README for the exception table and limitations.

This policy supplies no historical memberships, allocation weights, successor
relations, or reinterpretation of source S19 as TWN. Such additions need their
own explicit provenance and temporal semantics. Country descriptions belong to
a separate country dataset, consistent with the sibling TiVA and FAOSTAT maps.

These hashes record the inspected inputs. Maven checks repository checksums
on download; the recorded SHA-256 values above remain provenance and are not
separately enforced by the build.
