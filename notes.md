# Dynamic behaviour
- Basic: HP beforehand, reject if not acceptable
- Continuous: Reconfiguration at each step
    - Conservative: Respect current vSDNs
    - Liberal: Maximize A current+new
    - Maximize other metrics like utilization
- Periodic: Reconfiguration at given times or at low acceptance

# QoS
- Does more H means higher A? (static and dynamic analysis)
- How to handle QoS classes?

# Metrics
- no. accepted requests
- utilization (considering vSDN size)
- total deployment time
- 

# Log
- vSDN request history (start, end, deployed time, QoS)

# VSDN request
- TTL to deploy, to operate
- Cost of acceptance (trade-off)
- QoS class
- TTL generator
- QoS generator

# Hypervisor reconfiguration
- min. No. hypervisors to solve migration
- reconfiguration
- no reject optimal, optimal at every state