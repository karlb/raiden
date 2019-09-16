from math import sqrt

from raiden.constants import DAI_TOKEN_NETWORK_ADDRESS, WETH_TOKEN_NETWORK_ADDRESS
from raiden.settings import DEFAULT_DAI_FLAT_FEE, DEFAULT_WETH_FLAT_FEE, MediationFeeConfig
from raiden.utils.typing import Dict, FeeAmount, ProportionalFeeAmount, TokenAddress, Tuple


def ppm_fee_per_channel(per_hop_fee: ProportionalFeeAmount) -> ProportionalFeeAmount:
    """
    Converts proportional-fee-per-mediation into proportional-fee-per-channel

    Input and output are given in parts-per-million (ppm).

    See https://raiden-network-specification.readthedocs.io/en/latest/mediation_fees.html
    #converting-per-hop-proportional-fees-in-per-channel-proportional-fees
    for how to get to this formula.
    """
    per_hop_ratio = per_hop_fee / 1e6
    return ProportionalFeeAmount(round(per_hop_ratio / (per_hop_ratio + 2) * 1e6))


def adjust_proportional_fee(given_propoprtional_fee) -> ProportionalFeeAmount:
    """
     Given prop. fee also counts per mediation, therefore it needs to be adjusted on
     a per-channel basis:
     x * (1 - p) * (1 - p) = x * (1 - q)
     where
        x = payment amount
        q = cli proportional fee
        p = per channel proportional fee
     Leads to: p = 1 - sqrt(1 - q)
"""
    proportional_fee_ratio = given_propoprtional_fee / 1e6
    channel_prop_fee_ratio = 1 - sqrt(1 - proportional_fee_ratio)
    channel_prop_fee = round(channel_prop_fee_ratio * 1e6)
    return ProportionalFeeAmount(channel_prop_fee)


def prepare_mediation_fee_config(
    cli_token_to_flat_fee: Tuple[Tuple[TokenAddress, FeeAmount], ...],
    cli_token_to_proportional_fee: Tuple[Tuple[TokenAddress, ProportionalFeeAmount], ...],
    cli_token_to_proportional_imbalance_fee: Tuple[
        Tuple[TokenAddress, ProportionalFeeAmount], ...
    ],
) -> MediationFeeConfig:
    """ Converts the mediation fee CLI args to proper per-channel
    mediation fees. """
    tn_to_flat_fee: Dict[TokenAddress, FeeAmount] = {}
    # Add the defaults for flat fees for DAI/WETH
    tn_to_flat_fee[WETH_TOKEN_NETWORK_ADDRESS] = FeeAmount(DEFAULT_WETH_FLAT_FEE // 2)
    tn_to_flat_fee[DAI_TOKEN_NETWORK_ADDRESS] = FeeAmount(DEFAULT_DAI_FLAT_FEE // 2)

    # Store the flat fee settings for the given token addresses
    # The given flat fee is for the whole mediation, but that includes two channels.
    # Therefore divide by 2 here.
    for address, fee in cli_token_to_flat_fee:
        tn_to_flat_fee[address] = FeeAmount(fee // 2)

    tn_to_proportional_fee: Dict[TokenAddress, ProportionalFeeAmount] = {
        address: ppm_fee_per_channel(prop_fee)
        for address, prop_fee in cli_token_to_proportional_fee
    }

    tn_to_proportional_imbalance_fee: Dict[TokenAddress, ProportionalFeeAmount] = {
        address: ppm_fee_per_channel(prop_fee)
        for address, prop_fee in cli_token_to_proportional_imbalance_fee
    }

    return MediationFeeConfig(
        token_to_flat_fee=tn_to_flat_fee,
        token_to_proportional_fee=tn_to_proportional_fee,
        token_to_proportional_imbalance_fee=tn_to_proportional_imbalance_fee,
    )