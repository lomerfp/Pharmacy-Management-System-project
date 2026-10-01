# Academic Project Report and Presentation Outline

## Report chapters

1. **Introduction:** problem statement, objectives, scope, significance, assumptions, and limitations.
2. **Literature/context:** relational database principles, transaction systems, pharmacy inventory and expiry challenges.
3. **Requirements analysis:** stakeholder roles, use cases, functional/non-functional requirements, acceptance criteria, traceability.
4. **System analysis and design:** architecture, system boundary, DFD context/level 1, user workflows, security boundaries.
5. **Database design:** conceptual Chen ERD, logical Crow's Foot ERD, relational schema, data dictionary, keys/constraints, 1NF-to-3NF reasoning, physical MySQL/InnoDB indexes.
6. **Implementation:** React client, Django REST validation/services, MySQL migrations, FEFO and receipt/checkout transactions, UTC/Kampala handling.
7. **Testing and evaluation:** test strategy, actual environment, test cases/results, MySQL concurrency evidence, acceptance/UAT outcomes, requirements coverage.
8. **Operations:** setup, deployment assumptions, backup and restoration procedure, monitoring, account/security administration.
9. **Conclusion and future work:** limitations, supplier batch provenance, integration and scale backlog.

Include actual executed evidence only. Clearly distinguish SQLite unit tests from MySQL integration tests and do not claim legal or regulatory certification.

## Presentation outline

1. Project context and pharmacy workflow problem.
2. Scope, objectives, and SDLC/Database Development Life Cycle.
3. User roles and use-case walkthrough.
4. Conceptual ERD and approved 15-entity model.
5. Normalization, constraints, and deliberate snapshots.
6. Architecture and API/service transaction boundaries.
7. Purchase-to-receipt and FEFO sale/payment demonstration.
8. Security and audit design.
9. Test evidence and environment limitations.
10. Known issues, future work, and evaluation against objectives.
