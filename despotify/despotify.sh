#!/bin/bash

if [ -n "${NOTICE_URL}" ] ; then
  echo "notice_url: ${NOTICE_URL}"
  echo "notice_url=${NOTICE_URL}" >> /despotify.ini
fi  

if [ -n "${SLACK_URL}" ] ; then
  echo "slack_url: ${SLACK_URL}"
  echo "slack_url=${SLACK_URL}" >> /despotify.ini
fi  

if [ -n "${SLACK_CHANNEL}" ] ; then
  echo "slack_channel: ${SLACK_CHANNEL}"
  echo "slack_channel=${SLACK_CHANNEL}" >> /despotify.ini
fi  

if [ -n "${SLACK_USERNAME}" ] ; then
  echo "slack_username: ${SLACK_USERNAME}"
  echo "slack_username=${SLACK_USERNAME}" >> /despotify.ini
fi  

if [ -n "${INST_ID_URL}" ] ; then
  echo "inst_id_url: ${INST_ID_URL}"
  echo "inst_id_url=${INST_ID_URL}" >> /despotify.ini
fi  

if [ -n "${INST_IDENTITY_URL}" ] ; then
  echo "inst_identity_url: ${INST_IDENTITY_URL}"
  echo "inst_identity_url=${INST_IDENTITY_URL}" >> /despotify.ini
fi  

if [ -n "${DETACH_FROM_ASG}" ] ; then
  echo "detach_from_asg: ${DETACH_FROM_ASG}"
  echo "detach_from_asg=${DETACH_FROM_ASG}" >> /despotify.ini
fi  

exec python /despotify.py
