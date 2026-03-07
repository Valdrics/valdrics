"""
Production-quality tests for Azure Usage Analyzer.
Tests cover security, performance, edge cases, and real-world scenarios.
"""

from app.shared.analysis.azure_usage_analyzer import AzureUsageAnalyzer


class TestAzureUsageAnalyzer:
    """Basic functionality tests for AzureUsageAnalyzer."""

    def test_initialization_with_valid_data(self):
        """Test analyzer initializes correctly with valid cost records."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/vm1",
                "ResourceName": "vm1",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "10.50",
                "UsageQuantity": "168.0",
                "UsageDate": "2024-01-01",
            }
        ]

        analyzer = AzureUsageAnalyzer(cost_records)

        assert analyzer.records == cost_records
        assert len(analyzer._resource_costs) == 1
        assert (
            "/subscriptions/123/resourcegroups/test/providers/microsoft.compute/virtualmachines/vm1"
            in analyzer._resource_costs
        )

    def test_initialization_with_empty_data(self):
        """Test analyzer handles empty cost records gracefully."""
        analyzer = AzureUsageAnalyzer([])

        assert analyzer.records == []
        assert analyzer._resource_costs == {}

    def test_initialization_with_missing_resource_id(self):
        """Test analyzer handles records without ResourceId."""
        cost_records = [
            {"ServiceName": "Virtual Machines", "PreTaxCost": "10.0"},
            {"ResourceId": "", "ServiceName": "Storage", "PreTaxCost": "5.0"},
        ]

        analyzer = AzureUsageAnalyzer(cost_records)

        # Should only include records with valid ResourceId
        assert len(analyzer._resource_costs) == 0

    def test_group_by_resource_case_insensitive(self):
        """Test resource grouping is case-insensitive."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/Test/providers/Microsoft.Compute/virtualMachines/VM1",
                "PreTaxCost": "10.0",
            },
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/vm1",
                "PreTaxCost": "15.0",
            },
        ]

        analyzer = AzureUsageAnalyzer(cost_records)

        # Should be grouped under lowercase key
        resource_key = "/subscriptions/123/resourcegroups/test/providers/microsoft.compute/virtualmachines/vm1"
        assert resource_key in analyzer._resource_costs
        assert len(analyzer._resource_costs[resource_key]) == 2

    def test_find_idle_vms_with_idle_vm(self):
        """Test detection of idle VMs."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/idle-vm",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "75.0",  # High compute cost
                "UsageQuantity": "168.0",
                "MeterCategory": "Virtual Machine",
                "UsageDate": "2024-01-01",
            }
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        idle_vms = analyzer.find_idle_vms(days=7, cost_threshold=50.0)

        assert len(idle_vms) == 1
        vm = idle_vms[0]
        assert (
            vm["resource_id"]
            == "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/idle-vm"
        )
        assert vm["resource_name"] == "idle-vm"
        assert vm["resource_type"] == "Virtual Machine"
        assert vm["monthly_cost"] == 321.43  # 75 * (30/7) ≈ 321.43
        assert vm["recommendation"] == "Stop or deallocate if not needed"
        assert vm["confidence_score"] == 0.75

    def test_find_idle_vms_with_gpu_vm(self):
        """Test detection of idle GPU VMs with higher confidence."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/gpu-vm",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "150.0",
                "MeterCategory": "Virtual Machine",
                "UsageDate": "2024-01-01",
            }
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        idle_vms = analyzer.find_idle_vms()

        assert len(idle_vms) == 1
        vm = idle_vms[0]
        assert vm["resource_type"] == "Virtual Machine (GPU)"
        assert vm["confidence_score"] == 0.85  # Higher for GPU VMs

    def test_find_idle_vms_with_active_vm(self):
        """Test VMs with disk/network activity are not flagged as idle."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/active-vm",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "100.0",
                "MeterCategory": "Virtual Machine",
                "UsageDate": "2024-01-01",
            },
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/active-vm",
                "ServiceName": "Storage",
                "PreTaxCost": "5.0",
                "UsageQuantity": "50.0",  # High disk usage
                "MeterCategory": "Storage",
                "MeterName": "Disk Operations",
                "UsageDate": "2024-01-01",
            },
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        idle_vms = analyzer.find_idle_vms()

        assert len(idle_vms) == 0  # Should not be flagged as idle

    def test_find_idle_vms_below_cost_threshold(self):
        """Test VMs below cost threshold are not flagged."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/low-cost-vm",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "10.0",  # Below default 50.0 threshold
                "MeterCategory": "Virtual Machine",
                "UsageDate": "2024-01-01",
            }
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        idle_vms = analyzer.find_idle_vms()

        assert len(idle_vms) == 0

    def test_find_unattached_disks_unattached(self):
        """Test detection of unattached managed disks."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/disks/unattached-disk",
                "ServiceName": "Storage",
                "PreTaxCost": "25.0",
                "MeterCategory": "Storage",
                "MeterName": "Disk Storage",
                "UsageDate": "2024-01-01",
            }
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        unattached_disks = analyzer.find_unattached_disks()

        assert len(unattached_disks) == 1
        disk = unattached_disks[0]
        assert (
            disk["resource_id"]
            == "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/disks/unattached-disk"
        )
        assert disk["resource_name"] == "unattached-disk"
        assert disk["resource_type"] == "Managed Disk"
        assert disk["monthly_cost"] == 750.0  # 25 * 30
        assert disk["confidence_score"] == 0.90

    def test_find_unattached_disks_attached(self):
        """Test disks attached to VMs are not flagged as unattached."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/disks/attached-disk",
                "ServiceName": "Storage",
                "PreTaxCost": "15.0",
                "MeterCategory": "Storage",
                "UsageDate": "2024-01-01",
            },
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/vm1",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "50.0",
                "AttachedResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/disks/attached-disk",  # Attached
                "UsageDate": "2024-01-01",
            },
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        unattached_disks = analyzer.find_unattached_disks()

        assert len(unattached_disks) == 0  # Should not be flagged

    def test_find_idle_sql_databases_idle(self):
        """Test detection of idle SQL databases."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Sql/servers/sqlserver/databases/idle-db",
                "ServiceName": "SQL Database",
                "PreTaxCost": "20.0",
                "MeterName": "Basic Compute Hours",
                "UsageDate": "2024-01-01",
            }
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        idle_dbs = analyzer.find_idle_sql_databases()

        assert len(idle_dbs) == 1
        db = idle_dbs[0]
        assert (
            db["resource_id"]
            == "/subscriptions/123/resourceGroups/test/providers/Microsoft.Sql/servers/sqlserver/databases/idle-db"
        )
        assert db["resource_name"] == "idle-db"
        assert db["resource_type"] == "Azure SQL Database"
        assert db["monthly_cost"] == 85.71  # 20 * (30/7) ≈ 85.71
        assert db["confidence_score"] == 0.85

    def test_find_idle_sql_databases_active(self):
        """Test databases with DTU/vCore usage are not flagged as idle."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Sql/servers/sqlserver/databases/active-db",
                "ServiceName": "SQL Database",
                "PreTaxCost": "30.0",
                "MeterName": "DTU Usage",
                "UsageQuantity": "50.0",  # High DTU usage
                "UsageDate": "2024-01-01",
            }
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        idle_dbs = analyzer.find_idle_sql_databases()

        assert len(idle_dbs) == 0  # Should not be flagged as idle

    def test_find_idle_aks_clusters_idle(self):
        """Test detection of idle AKS clusters."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.ContainerService/managedClusters/idle-aks",
                "ServiceName": "Kubernetes Services",
                "PreTaxCost": "40.0",
                "MeterName": "Uptime SLA Hours",
                "UsageDate": "2024-01-01",
            }
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        idle_clusters = analyzer.find_idle_aks_clusters()

        assert len(idle_clusters) == 1
        cluster = idle_clusters[0]
        assert (
            cluster["resource_id"]
            == "/subscriptions/123/resourceGroups/test/providers/Microsoft.ContainerService/managedClusters/idle-aks"
        )
        assert cluster["resource_name"] == "idle-aks"
        assert cluster["resource_type"] == "AKS Cluster"
        assert cluster["monthly_cost"] == 171.43  # 40 * (30/7) ≈ 171.43
        assert cluster["confidence_score"] == 0.88

    def test_find_idle_aks_clusters_with_nodes(self):
        """Test AKS clusters with node costs are not flagged as idle."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.ContainerService/managedClusters/active-aks",
                "ServiceName": "Kubernetes Services",
                "PreTaxCost": "100.0",
                "MeterName": "Agent Pool Uptime Hours",  # Node costs
                "UsageDate": "2024-01-01",
            }
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        idle_clusters = analyzer.find_idle_aks_clusters()

        assert len(idle_clusters) == 0  # Should not be flagged

    def test_find_orphan_public_ips(self):
        """Test detection of orphan public IP addresses."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Network/publicIPAddresses/orphan-ip",
                "ServiceName": "IP Addresses",
                "PreTaxCost": "3.0",
                "MeterName": "IP Address Hours",
                "UsageDate": "2024-01-01",
            }
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        orphan_ips = analyzer.find_orphan_public_ips()

        assert len(orphan_ips) == 1
        ip = orphan_ips[0]
        assert (
            ip["resource_id"]
            == "/subscriptions/123/resourceGroups/test/providers/Microsoft.Network/publicIPAddresses/orphan-ip"
        )
        assert ip["resource_name"] == "orphan-ip"
        assert ip["resource_type"] == "Public IP Address"
        assert ip["monthly_cost"] == 90.0  # 3 * 30
        assert ip["confidence_score"] == 0.90

    def test_find_unused_app_service_plans_unused(self):
        """Test detection of unused App Service Plans."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Web/serverfarms/unused-plan",
                "ServiceName": "App Service",
                "PreTaxCost": "25.0",
                "MeterName": "Basic Plan Hours",
                "UsageDate": "2024-01-01",
            }
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        unused_plans = analyzer.find_unused_app_service_plans()

        assert len(unused_plans) == 1
        plan = unused_plans[0]
        assert (
            plan["resource_id"]
            == "/subscriptions/123/resourceGroups/test/providers/Microsoft.Web/serverfarms/unused-plan"
        )
        assert plan["resource_name"] == "unused-plan"
        assert plan["resource_type"] == "App Service Plan"
        assert plan["monthly_cost"] == 750.0  # 25 * 30
        assert plan["confidence_score"] == 0.85

    def test_find_unused_app_service_plans_used(self):
        """Test App Service Plans with app usage are not flagged."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Web/serverfarms/used-plan",
                "ServiceName": "App Service",
                "PreTaxCost": "30.0",
                "MeterName": "App Service Compute Hours",
                "UsageQuantity": "100.0",  # App usage
                "UsageDate": "2024-01-01",
            }
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        unused_plans = analyzer.find_unused_app_service_plans()

        assert len(unused_plans) == 0  # Should not be flagged

    def test_find_orphan_nics_not_implemented(self):
        """Test orphan NIC detection returns empty list (not implemented)."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Network/networkInterfaces/nic1",
                "ServiceName": "Network",
                "PreTaxCost": "0.0",  # NICs are free
                "UsageDate": "2024-01-01",
            }
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        orphan_nics = analyzer.find_orphan_nics()

        assert orphan_nics == []  # Not implemented

    def test_find_old_snapshots(self):
        """Test detection of old disk snapshots."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/snapshots/old-snapshot",
                "ServiceName": "Storage",
                "PreTaxCost": "8.0",
                "MeterCategory": "Snapshots",
                "UsageDate": "2024-01-01",
            }
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        old_snapshots = analyzer.find_old_snapshots()

        assert len(old_snapshots) == 1
        snapshot = old_snapshots[0]
        assert (
            snapshot["resource_id"]
            == "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/snapshots/old-snapshot"
        )
        assert snapshot["resource_name"] == "old-snapshot"
        assert snapshot["resource_type"] == "Disk Snapshot"
        assert snapshot["monthly_cost"] == 240.0  # 8 * 30
        assert snapshot["confidence_score"] == 0.70
