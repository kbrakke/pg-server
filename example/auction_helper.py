import requests
import logging
import json
import datetime
import pprint

pp = pprint.PrettyPrinter(indent=4)
from constants import SERVER_HOST, SERVER_PORT, MONEY
server_url = SERVER_HOST + ":" + SERVER_PORT

logger = logging.getLogger('Auction Helper')
logger.setLevel(logging.INFO)
fh = logging.FileHandler('auction-helper' + str(datetime.datetime.now().time().microsecond) + '.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


def main(player, market_state, auction_state, resource_state, all_players_state, player_token):
    logger.info("Player: " + player.get('info').get('name'))
    if auction_state.get('auction_in_progress') == False:
        # Bid of new powerplant
        roi, best_plant = best_power_plant(market_state.get("current_market"), resource_state)
        logger.info(f'With a ROI of {roi:.3f}, the best powerplant is currently')
        logger.info(best_plant)
        #prettyPrintResources(resource_state, best_plant.get("resource_type"))
        powerplant_id = best_plant.get("market_cost")
        response = bid(player.get('info').get('name'),
                       player_token, powerplant_id, powerplant_id)
        if response.get('status') != 'SUCCESS':
            print(response.get('msg'))
    else:
        # Auction is in progress
        powerplant = auction_state.get('powerplant')
        powerplant_id = powerplant.get('market_cost')
        current_bid = auction_state.get('current_bid')
        current_roi = powerplant_roi(powerplant, current_bid, resource_state)
        other_current_market = [ x for x in market_state.get("current_market") if x.get("market_cost") != powerplant_id ]
        next_best_roi, nextBestPlant = best_power_plant(other_current_market + [market_state.get("futures_market")[0]], resource_state)
        #We have better options coming up, so pass
        if (next_best_roi > current_roi):
            logger.info(f'With a ROI of {next_best_roi:.3f}, we want the new plant')
            logger.info(nextBestPlant)
            response = bid(player.get('info').get('name'),
                           player_token, -1, powerplant_id)
            if response.get('status') != 'SUCCESS':
                print(response.get('msg'))
        else:
            response = bid(player.get('info').get('name'),
                player_token, current_bid + 1, powerplant_id)
            if response.get('status') != 'SUCCESS':
                print(response.get('msg'))
            


def bid(player_name, player_token, amt, powerplant_id):
    payload = dict(player_name=player_name,
                   powerplant_id=powerplant_id, bid=amt)
    response = requests.post(
        server_url + "/bid", json=payload, cookies=player_token).json()
    return response

# Look available market and pick the power plant with the best ROI to run twice
def best_power_plant(powerplants, resource_state):
    logger.info(powerplants)
    bestRoi = -1
    bestPowerplant = None
    for powerplant in powerplants:
        roi = powerplant_roi(powerplant, powerplant.get("market_cost"), resource_state)
        if roi > bestRoi:
            bestPowerplant = powerplant
            bestRoi = roi
    return bestRoi, bestPowerplant

def powerplant_roi(powerplant, currentBid, resource_state):
    moneyForTwoRuns = MONEY[powerplant.get("generators")] * 2
    cost = currentBid + cost_for_n_resources(
        resource_state,
        powerplant.get("resource_type"),
        2 * powerplant.get("resource_cost")
    )
    return float(moneyForTwoRuns/cost)

def cost_for_n_resources(resources, resource, number):
    #logger.info(resources)
    #prettyPrintResources(resources, resource)
    totalCost = 0
    resourcesToBuy = number
    if resource == "CLEAN":
        return 0
    if resource == "HYBRID":
        #Working on it
        return 20
    else:
        resource_array = resources.get(resource)
        lowestBucketIndex = getLowestBucketIndex(resources.get(resource))
        while resourcesToBuy > 0:
            cost, _, current = resource_array[lowestBucketIndex]
            if current <= resourcesToBuy:
                totalCost += cost * resourcesToBuy
                return totalCost
            if current < resourcesToBuy:
                totalCost += cost * current
                resourcesToBuy -= current
                lowestBucketIndex -= 1
                if lowestBucketIndex < 0:
                    return totalCost


def getLowestBucketIndex(resource_array):
    for i, bucket in enumerate(resource_array):
        if (bucket[2] < bucket[1]):
            return i
    return resource_array.length - 1

def prettyPrintResources(resource_state, resource):
    if resource == "HYBRID":
        logger.info("not pretty printing hybrid")
        return
    resourceArray =  resource_state[resource]
    resourceChar = resource[0]
    #top line +-----+----+----+---+---+--+--+--+
    topLine = "+"
    topLine += "-" * len(resource)
    middleLine = "|"
    middleLine += resource
    for bucket in reversed(resourceArray):
        topLine += "+"
        topLine += "-" *bucket[1]

        middleLine += "|"
        missing = bucket[1] - bucket[2]
        middleLine += "-" * missing
        middleLine += resourceChar * bucket[2]
    topLine += "+"
    middleLine += "|"
    logger.info(topLine)
    logger.info(middleLine)
    logger.info(topLine)

        



