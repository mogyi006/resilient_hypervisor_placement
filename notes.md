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


# Hypervisor Load
- Hypervisor capacity as parameter
- Secondary objective to minimize the max hypervisor load
- Tradeoff between hypervisor and controller load

# Results

## No. hypervisors
- '../results/25_italy/static/tmp/2023-04-03-21-43-35/simulation-group-results.json'
- '../results/25_italy/static/tmp/2023-04-16-14-16-49/simulation-group-results.json'

- '../results/26_usa/static/tmp/2023-04-03-21-44-07/simulation-group-results.json'

## Hypervisor Capacity
- '../results/25_italy/static/tmp/2023-04-06-20-50-28/simulation-group-results.json'
- '../results/26_usa/static/tmp/2023-04-06-20-54-15/simulation-group-results.json'

- '../results/25_italy/static/tmp/2023-04-07-12-13-38/simulation-group-results.json'
- '../results/26_usa/static/tmp/2023-04-07-12-13-59/simulation-group-results.json'

- '../results/25_italy/static/tmp/2023-04-07-17-55-40/simulation-group-results.json'

## Heuristic
Fine heatmap of IT-US networks

### Latency - 0.7

### Latency - 0.6
IT
    '../results/25_italy/static/tmp/2023-04-19-18-26-47/simulation-group-results.json', # 1-50
    '../results/25_italy/static/tmp/2023-04-19-20-20-18/simulation-group-results.json', # 100-400

    '../results/25_italy/static/tmp/2023-04-19-20-38-09/simulation-group-results.json', # FULL

US
    '../results/26_usa/static/tmp/2023-04-15-16-41-05/simulation-group-results.json', # 1-100
    '../results/26_usa/static/tmp/2023-04-16-10-54-03/simulation-group-results.json', # 200, 400
    '../results/26_usa/static/tmp/2023-04-19-18-38-31/simulation-group-results.json', # 0.3, 0.5
    '../results/26_usa/static/tmp/2023-04-16-11-00-13/simulation-group-results.json' # ILP

    '../results/26_usa/static/tmp/2023-04-19-20-39-58/simulation-group-results.json', # FULL

### Latency - 0.5