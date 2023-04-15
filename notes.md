# Dynamic behaviour
- Basic: HP beforehand, reject if not acceptable
- Continuous: Reconfiguration at each step
    - Conservative: Respect current vSDNs
    - Liberal: Maximize A current+new
    - Maximize other metrics like utilization
- Periodic: Reconfiguration at given times or at low acceptance

# QoS
- Does more H means higher A? (static and dynamic analysis)
    - Yes, 1-2 additional hypervisor significantly increases A.
- How to handle QoS classes?

# Metrics
- no. accepted requests
- no. deployed vSDN nodes
- total deployment time
- utilization = size*TTL
- revenue = utilization*QoS
- flexibility: no. possible hypervisor pairs

The metrics behave similarly, only a small variation can be observed.

# Flexibility
- no. possible controller locations ()
    - Usually only a few controller locations are used.
    - Maybe maximize the number of controllers at a node (max 25% at one node)

- no. possible hypervisor pairs (flexibility for new placement)
    - The best hypervisor locations similarly to the best controller locations are in the center of the network.
    - Therefore if we optimize for hypervisor flexibility, the same controllers will be used.

Without constraints the best locations will be the same.

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

# TODO
- Capacitated:
    - Hypervisor capacity
    - Controller capacity
- Smart representative set selection
- Soft latency requirement
- genetic algo
- placement kiértékelése a biztositott latency alapján
- Flexibility Weight simulation
- Max 1 hypervisor migration per timestep


# Results

## No. hypervisors
- '../results/25_italy/static/tmp/2023-04-03-21-43-35/simulation-group-results.json'
- '../results/26_usa/static/tmp/2023-04-03-21-44-07/simulation-group-results.json'

## Hypervisor Capacity
- '../results/25_italy/static/tmp/2023-04-06-20-50-28/simulation-group-results.json'
- '../results/26_usa/static/tmp/2023-04-06-20-54-15/simulation-group-results.json'

- '../results/25_italy/static/tmp/2023-04-07-12-13-38/simulation-group-results.json'
- '../results/26_usa/static/tmp/2023-04-07-12-13-59/simulation-group-results.json'

- '../results/25_italy/static/tmp/2023-04-07-17-55-40/simulation-group-results.json'

## Heuristic

### Latency - 0.7
- '../results/26_usa/static/tmp/2023-03-30-08-04-19/simulation-group-results.json'

### Latency - 0.6
- '../results/25_italy/static/tmp/2023-03-29-16-57-50/simulation-group-results.json'
- '../results/26_usa/static/tmp/2023-03-29-20-23-51/simulation-group-results.json'
- '../results/37_cost/static/tmp/2023-03-29-21-25-50/simulation-group-results.json'

### Latency - 0.5
- '../results/25_italy/static/tmp/2023-03-30-08-03-55/simulation-group-results.json'